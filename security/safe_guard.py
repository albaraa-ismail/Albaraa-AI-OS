import os
import re
import threading
import time
import traceback
from typing import Any

from core.core_ai import sb, send_msg

ADMIN_PHONE = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
_RATE_TRACKER: dict[str, list[float]] = {}
_STRIKE_COUNT: dict[str, int] = {}
_BLACKLIST: set[str] = set()

INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "EN_IGNORE_INSTRUCTIONS"),
    (r"(reveal|show|print|dump|export)\s+(system\s+prompt|api[_\s]?key|env|secrets|token|password)", "EN_SECRET_EXTRACTION"),
    (r"(?:__import__\s*\(|os\.system\s*\(|subprocess\.popen\s*\()", "CODE_EXEC_ATTEMPT"),
    (r"تجاهل\s+(كل\s+|جميع\s+)?التعليمات\s+(السابقة|الأولى)", "AR_IGNORE_INSTRUCTIONS"),
    (r"(اعرض|اظهر|أظهر|اطبع|هات|عطني)\s+(مفاتيح|كلمات\s+المرور|الأسرار|التعليمات\s+البرمجية|متغيرات)", "AR_SECRET_EXTRACTION"),
    (r"(drop\s+table|delete\s+from|union\s+select|;\s*--|<script>|javascript:)", "SQL_XSS_PAYLOAD"),
]

SAUDI_RESTRICTED_PATTERNS = [
    r"(اختراق|تهكير|تزوير\s+وثائق|غسيل\s+أموال|ترويج\s+ممنوعات)",
]


def _is_admin(cid: str) -> bool:
    if not cid or not ADMIN_PHONE:
        return False
    digits = "".join(filter(str.isdigit, cid.split("@")))
    if digits == ADMIN_PHONE:
        return True
    return len(digits) >= 9 and len(ADMIN_PHONE) >= 9 and digits[-9:] == ADMIN_PHONE[-9:]


def check_rate_limit(cid: str, max_per_min: int = 12) -> bool:
    if _is_admin(cid):
        return True
    if cid in _BLACKLIST:
        return False
    now = time.time()
    history = [t for t in _RATE_TRACKER.get(cid, []) if now - t < 60]
    if len(history) >= max_per_min:
        return False
    history.append(now)
    _RATE_TRACKER[cid] = history
    return True


def mask_saudi_pii(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\b[12]\d{9}\b", "[هوية_محمية_PDPL]", text)
    text = re.sub(r"\bSA\d{22}\b", "[حساب_بنكي_محمي_PDPL]", text, flags=re.IGNORECASE)
    return text


def apply_saudi_governance(task_type: str, content: str) -> str:
    clean = mask_saudi_pii(content)
    low = task_type.lower()
    if any(k in low for k in ("فاتورة", "عرض سعر", "ضريبة", "مالية")):
        clean += "\n\n[ملاحظة امتثال نظامي: تطبق ضريبة القيمة المضافة 15% وفق متطلبات هيئة الزكاة والضريبة والجمارك ZATCA]."
    elif any(k in low for k in ("عقد", "اتفاقية", "مذكرة تفاهم", "نظام العمل")):
        clean += "\n\n[إخلاء مسؤولية نظامي: هذه المسودة استرشادية ومصاغة وفق الأنظمة السعودية، ويوصى بمراجعتها من مستشار قانوني معتمد قبل التوقيع]."
    elif any(k in low for k in ("موقع", "متجر", "استبيان")):
        clean += "\n<!-- متوافق مع ضوابط نظام حماية البيانات الشخصية السعودي (PDPL) ونظام التجارة الإلكترونية -->"
    return clean


def _record_security_strike(cid: str, rule_name: str, snippet: str) -> None:
    if not cid or _is_admin(cid):
        return
    count = _STRIKE_COUNT.get(cid, 0) + 1
    _STRIKE_COUNT[cid] = count
    threading.Thread(
        target=sb,
        args=("POST", "self_learning_logs", {
            "user_role": "security_alert",
            "lesson_learned": f"[ALERT] CID={cid} | Rule={rule_name} | Strike={count} | Msg={snippet[:60]}",
            "is_active": True,
        }),
        daemon=True,
    ).start()
    if count >= 3:
        _BLACKLIST.add(cid)
        if ADMIN_PHONE:
            send_msg(
                f"{ADMIN_PHONE}@c.us",
                f"🚨 *تنبيه أمني عاجل (حظر تلقائي):*\nتم حظر المستخدم `{cid}` لتكرار محاولات التلاعب ({rule_name}).",
            )


def inspect_prompt_injection(text: str, cid: str = "") -> dict[str, Any]:
    if not text:
        return {"is_safe": True, "matched_rule": None}
    if cid in _BLACKLIST and not _is_admin(cid):
        return {"is_safe": False, "matched_rule": "BLACKLISTED_USER"}
    if cid and not check_rate_limit(cid):
        return {"is_safe": False, "matched_rule": "RATE_LIMIT_EXCEEDED"}

    low = text.lower()
    for pattern, rule_name in INJECTION_PATTERNS:
        if re.search(pattern, low, flags=re.IGNORECASE):
            _record_security_strike(cid, rule_name, text)
            return {"is_safe": False, "matched_rule": rule_name}

    for sp in SAUDI_RESTRICTED_PATTERNS:
        if re.search(sp, low, flags=re.IGNORECASE):
            _record_security_strike(cid, "SAUDI_LAW_VIOLATION", text)
            return {"is_safe": False, "matched_rule": "SAUDI_LAW_VIOLATION"}

    return {"is_safe": True, "matched_rule": None}


def safe_run(func: Any, *args: Any, **kwargs: Any) -> Any:
    cid = next(
        (a for a in args if isinstance(a, str) and ("@c.us" in a or "@g.us" in a or a.startswith("web_"))),
        None,
    )
    t0 = time.time()
    try:
        res = func(*args, **kwargs)
        elapsed = round(time.time() - t0, 2)
        threading.Thread(
            target=sb,
            args=("POST", "telemetry_kpis", {
                "user_role": cid or "system",
                "unit_used": getattr(func, "__name__", "task"),
                "response_time_sec": elapsed,
                "time_saved_min": 25,
                "user_growth_score": 96,
                "deliverable_type": getattr(func, "__name__", "general"),
            }),
            daemon=True,
        ).start()
        return res
    except Exception:
        full_err = traceback.format_exc()
        err = full_err.splitlines()[-1]
        print("GUARD CATCH:\n" + full_err, flush=True)
        if cid:
            send_msg(
                cid,
                f"⚠️ *تنبيه حماية النظام:*\nتعذر إكمال العملية الحالية ({err})، تم احتواء الخطأ بأمان والنظام جاهز لطلبك التالي.",
            )
        return None

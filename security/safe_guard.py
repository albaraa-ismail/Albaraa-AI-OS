import re
import traceback
from typing import Dict, Any
from core.core_ai import send_msg

INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "EN_IGNORE_INSTRUCTIONS"),
    (r"(reveal|show|print|dump)\s+(system\s+prompt|api[_\s]?key|env|secrets)", "EN_SECRET_EXTRACTION"),
    (r"تجاهل\s+(كل\s+|جميع\s+)?التعليمات\s+(السابقة|الأولى)", "AR_IGNORE_INSTRUCTIONS"),
    (r"(اعرض|اظهر|أظهر|اطبع|هات)\s+(مفاتيح|كلمات\s+المرور|الأسرار|التعليمات\s+البرمجية)", "AR_SECRET_EXTRACTION"),
    (r"(drop\s+table|union\s+select|;\s*--|<script>)", "SQL_XSS_PAYLOAD"),
]


def inspect_prompt_injection(text: str) -> Dict[str, Any]:
    """فحص استباقي للنصوص لاكتشاف محاولات الحقن النصي (Prompt Injection) أو استخراج الأسرار."""
    if not text:
        return {"is_safe": True, "matched_rule": None}
    low = text.lower()
    for pattern, rule_name in INJECTION_PATTERNS:
        if re.search(pattern, low, flags=re.IGNORECASE):
            return {"is_safe": False, "matched_rule": rule_name}
    return {"is_safe": True, "matched_rule": None}


def safe_run(func, *args, **kwargs):
    """غلاف حماية مرن يقبل أي عدد من المعاملات ويمنع انهيار الخادم عند حدوث خطأ."""
    cid = None
    for a in args:
        if isinstance(a, str) and ("@c.us" in a or "@g.us" in a or a.startswith("web_")):
            cid = a
            break
    try:
        return func(*args, **kwargs)
    except Exception:
        full_err = traceback.format_exc()
        err = full_err.splitlines()[-1]
        print("GUARD CATCH:\n" + full_err, flush=True)
        if cid:
            send_msg(cid, f"⚠ *تنبيه درع الحماية:*\nتعذر إكمال المهمة بسبب: `{err}`\nتم عزل الخطأ والنظام جاهز لأمرك التالي.")
        return None

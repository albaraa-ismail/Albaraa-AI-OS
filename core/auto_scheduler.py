import ast
import json
import time
import base64
import threading
from datetime import datetime
from typing import Any, Optional
import requests

from core.config import ADMIN_PHONE, GITHUB_API, GITHUB_REPO, GITHUB_TOKEN, RIYADH_TZ
from core.core_ai import ai_ask_json, sb
from core.event_bus import BUS
from core.orchestrator import send_msg
from telemetry.evolution_engine import analyze_system_evolution, check_due_reminders

_SCHEDULER_STARTED = False


def _gh_headers() -> dict[str, str]:
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}


def _gh_url(path: str) -> str:
    return f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path.strip()}"


def _first_record(data: Any) -> Optional[dict[str, Any]]:
    item = next(iter(data), None) if isinstance(data, list) else data
    return item if isinstance(item, dict) else None


def _load_proposal(pid: int) -> Optional[dict[str, Any]]:
    rec = _first_record(sb("GET", "self_learning_logs", q=f"?id=eq.{pid}"))
    if not rec:
        return None
    try:
        return json.loads(rec.get("lesson_learned", "{}"))
    except Exception:
        return None


def _get_gh_file(target_file: str) -> tuple[str, Optional[str]]:
    res = requests.get(_gh_url(target_file), headers=_gh_headers(), timeout=15)
    if res.status_code == 200:
        data = res.json()
        return base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore"), data.get("sha")
    return "", None


def _push_gh_file(target_file: str, content: str, msg: str, sha: Optional[str] = None) -> int:
    payload: dict[str, Any] = {"message": msg, "content": base64.b64encode(content.encode("utf-8")).decode("utf-8")}
    if sha:
        payload["sha"] = sha
    return requests.put(_gh_url(target_file), headers=_gh_headers(), json=payload, timeout=20).status_code


def propose_safe_upgrade(topic: str = "تحسين سرعة الاستجابة وجودة المخرجات") -> None:
    if not ADMIN_PHONE:
        return
    logs = sb("GET", "self_learning_logs", q="?order=id.desc&limit=10") or []
    notes = "\n".join(str(x.get("lesson_learned", ""))[:120] for x in logs if isinstance(x, dict))

    prompt = (
        f"بناء على السجل:\n{notes}\nالهدف: {topic}\n"
        "اقترح دالة بايثون مساعدة مستقلة وآمنة دون حذف أي دالة قائمة.\n"
        'أرجع JSON فقط: {"title": "عنوان", "target_file": "multimodal/pro_capabilities.py", '
        '"risk_level": "منخفض جدا", "new_libs": "لا يوجد", "summary": "شرح", "code": "كود بايثون صالح"}'
    )
    prop = ai_ask_json(prompt, "أنت مهندس برمجيات بايثون خبير. اكتب كودا نظيفا وآمنا.", mode="general")
    if not isinstance(prop, dict) or not prop.get("code"):
        return

    code_body = str(prop["code"]).replace("```python", "").replace("```", "").strip()
    try:
        ast.parse(code_body)
        prop["ast_status"] = "اجتاز فحص AST بنجاح 100%"
    except SyntaxError as exc:
        print(f"AST Rejected: L{exc.lineno} - {exc.msg}", flush=True)
        return

    prop["code"] = code_body
    saved = sb(
        "POST",
        "self_learning_logs",
        {"user_role": "evolution_proposal", "lesson_learned": json.dumps(prop, ensure_ascii=False), "is_active": True},
    )
    rec = _first_record(saved)
    pid = rec.get("id", 0) if rec else 0
    if not pid:
        return

    send_msg(
        f"{ADMIN_PHONE}@c.us",
        f"🛡️ *مقترح تطوير ذاتي جاهز (✅ AST)*\n• *الرقم:* `{pid}` | *العنوان:* {prop.get('title')}\n"
        f"• *الملف:* `{prop.get('target_file')}` | *المخاطرة:* {prop.get('risk_level')}\n"
        f"• *التفاصيل:* {prop.get('summary')}\n\n"
        f"📄 `عرض كود {pid}` | ✅ `اعتماد التطوير {pid}` | ❌ `رفض التطوير {pid}`",
    )


def get_proposal_code(pid: int) -> str:
    prop = _load_proposal(pid)
    if not prop:
        return "⚠️ لم يتم العثور على مقترح التطوير المطلوب."
    return f"📄 *كود التطوير #{pid} (`{prop.get('target_file')}`):*\n```python\n{prop.get('code', '')}\n```"


def approve_and_deploy_upgrade(pid: int) -> str:
    if not GITHUB_TOKEN:
        return "⚠️ متغير `GITHUB_TOKEN` غير مضبوط في Render."
    prop = _load_proposal(pid)
    if not prop:
        return "⚠️ لم يتم العثور على مقترح التطوير."

    try:
        target = prop.get("target_file", "multimodal/pro_capabilities.py").strip()
        old_content, sha = _get_gh_file(target)
        prop["backup_content"] = old_content
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(prop, ensure_ascii=False)}, q=f"?id=eq.{pid}")

        merged = f"{old_content}\n\n# --- Auto-Approved Upgrade #{pid} ---\n{prop.get('code', '')}\n"
        status = _push_gh_file(target, merged, f"Approved Upgrade #{pid}: {prop.get('title', '')}", sha)
        if status in (200, 201):
            return f"✅ *تم تثبيت التطوير #{pid} في `{target}` بنجاح!*\n↩️ للتراجع: `تراجع عن التطوير {pid}`"
        return f"⚠️ فشل التحديث على GitHub (رمز: {status})."
    except Exception as exc:
        return f"⚠️ خطأ أثناء التثبيت: {exc}"


def rollback_upgrade(pid: int) -> str:
    if not GITHUB_TOKEN:
        return "⚠️ متغير `GITHUB_TOKEN` غير مضبوط في Render."
    prop = _load_proposal(pid)
    if not prop or prop.get("backup_content") is None:
        return "⚠️ لا توجد نسخة احتياطية محفوظة لهذا التطوير."

    target = prop.get("target_file", "")
    _, sha = _get_gh_file(target)
    status = _push_gh_file(target, prop["backup_content"], f"Rollback Upgrade #{pid}", sha)
    return f"↩️ *تمت استعادة النسخة السابقة للملف `{target}`.*" if status in (200, 201) else f"⚠️ فشل التراجع ({status})."


def _scheduler_loop() -> None:
    admin_cid = f"{ADMIN_PHONE}@c.us" if ADMIN_PHONE else ""
    last_report = ""
    while True:
        try:
            now = datetime.now(RIYADH_TZ)
            for item in check_due_reminders():
                if target := (item.get("cid") or admin_cid):
                    send_msg(target, f"⏰ *تذكير مجدول:*\n{item.get('text', '')}")
                    BUS.publish("scheduler.reminder_sent", {"cid": target})

            today = now.strftime("%Y-%m-%d")
            if now.hour == 9 and now.minute < 5 and last_report != today:
                last_report = today
                if admin_cid and (report := analyze_system_evolution()):
                    send_msg(admin_cid, report)
                    BUS.publish("scheduler.daily_report_sent", {"date": today})
                propose_safe_upgrade()
        except Exception as exc:
            print(f"Scheduler Err: {exc}", flush=True)
        time.sleep(55)


def start_scheduler() -> Optional[threading.Thread]:
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED:
        return None
    _SCHEDULER_STARTED = True
    thread = threading.Thread(target=_scheduler_loop, daemon=True)
    thread.start()
    return thread

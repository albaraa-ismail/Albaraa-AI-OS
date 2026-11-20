import os
import ast
import json
import time
import base64
import threading
import requests
from datetime import datetime, timezone, timedelta
from core.core_ai import sb, ai_ask, ai_ask_json, send_msg
from core.event_bus import BUS
from telemetry.evolution_engine import analyze_system_evolution, check_due_reminders

RIYADH_TZ = timezone(timedelta(hours=3))
ADMIN_PHONE = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "albaraa-ismail/Albaraa-AI-OS").strip()


def _validate_python_syntax(code_str: str) -> tuple[bool, str]:
    try:
        ast.parse(code_str)
        return True, "تم اجتياز فحص القواعد البرمجية (AST) بنجاح 100%"
    except SyntaxError as e:
        return False, f"خطأ برمجي في السطر {e.lineno}: {e.msg}"


def propose_safe_upgrade(topic: str = "تحسين سرعة الاستجابة وجودة المخرجات"):
    if not ADMIN_PHONE:
        return
    admin_cid = f"{ADMIN_PHONE}@c.us"
    logs = sb("GET", "self_learning_logs", q="?order=id.desc&limit=10") or []
    recent_notes = "\n".join([str(x.get("lesson_learned", ""))[:120] for x in logs if isinstance(x, dict)])

    prompt = (
        f"بناءً على سجل التفاعل والملاحظات الأخيرة:\n{recent_notes}\n\n"
        f"مجال التحسين المستهدف: {topic}\n"
        "اقترح إضافة برمجية مستقلة آمنة (دالة بايثون مساعدة جديدة) يمكن إضافتها دون تعديل أو حذف أي دالة قائمة.\n"
        "أرجع JSON فقط بهذا الهيكل الدقيق:\n"
        '{"title": "عنوان التطوير", "target_file": "multimodal/pro_capabilities.py", "risk_level": "منخفض جداً (دالة مستقلة)", '
        '"new_libs": "لا يوجد", "summary": "شرح تفصيلي للفائدة والتغيير", "code": "كود بايثون صالح للتنفيذ المباشر"}'
    )
    proposal = ai_ask_json(prompt, "أنت مهندس برمجيات خبير في بايثون. اكتب كوداً نظيفاً وآمناً ومختبراً.", mode="general")
    if not isinstance(proposal, dict) or not proposal.get("code"):
        return

    code_body = str(proposal["code"]).replace("```python", "").replace("```", "").strip()
    is_valid, check_msg = _validate_python_syntax(code_body)
    if not is_valid:
        print(f"Evolution Rejected by AST: {check_msg}", flush=True)
        return

    proposal["code"] = code_body
    proposal["ast_status"] = check_msg
    saved = sb("POST", "self_learning_logs", {
        "user_role": "evolution_proposal",
        "lesson_learned": json.dumps(proposal, ensure_ascii=False),
        "is_active": True
    })
    pid = saved[0].get("id", 0) if isinstance(saved, list) and saved else 0
    if not pid:
        return

    msg = (
        f"🛡️ *مقترح تطوير ذاتي جاهز (اجتاز الفحص البرمجي ✅)*\n"
        f"• *رقم التطوير:* `{pid}`\n"
        f"• *العنوان:* {proposal.get('title', 'تحسين الأداء')}\n"
        f"• *الملف المستهدف:* `{proposal.get('target_file', 'multimodal/pro_capabilities.py')}`\n"
        f"• *المكتبات الجديدة:* {proposal.get('new_libs', 'لا يوجد')}\n"
        f"• *مستوى المخاطرة:* {proposal.get('risk_level', 'منخفض جداً')}\n"
        f"• *التفاصيل:* {proposal.get('summary', '')}\n\n"
        f"📄 *لعرض الكود الكامل قبل القرار اكتب:* `عرض كود {pid}`\n"
        f"✅ *للاعتماد والتثبيت الآمن اكتب:* `اعتماد التطوير {pid}`\n"
        f"❌ *للرفض والحذف اكتب:* `رفض التطوير {pid}`"
    )
    send_msg(admin_cid, msg)
def get_proposal_code(pid: int) -> str:
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{pid}")
    if not res:
        return "⚠️ لم يتم العثور على مقترح التطوير المطلوب."
    rec = res[0] if isinstance(res, list) else res
    try:
        prop = json.loads(rec.get("lesson_learned", "{}"))
        return (
            f"📄 *تفاصيل وكود التطوير رقم {pid}:*\n"
            f"• *الملف:* `{prop.get('target_file')}`\n"
            f"• *الفحص:* {prop.get('ast_status')}\n\n"
            f"```python\n{prop.get('code', '')}\n```"
        )
    except Exception:
        return "⚠️ تعذر قراءة بيانات المقترح."


def approve_and_deploy_upgrade(pid: int) -> str:
    if not GITHUB_TOKEN:
        return "⚠️ للتثبيت المباشر على GitHub، تأكد من إضافة `GITHUB_TOKEN` في إعدادات Render. يمكنك حالياً عرض الكود ونسخه يدوياً."
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{pid}")
    if not res:
        return "⚠️ لم يتم العثور على مقترح التطوير."
    rec = res if isinstance(res, list) else res
    try:
        prop = json.loads(rec.get("lesson_learned", "{}"))
        target_file = prop.get("target_file", "multimodal/pro_capabilities.py").strip()
        new_code = prop.get("code", "")

        url = f"https://github.com{GITHUB_REPO}/contents/{target_file}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r_get = requests.get(url, headers=headers, timeout=15)

        old_content = ""
        sha = None
        if r_get.status_code == 200:
            file_json = r_get.json()
            sha = file_json.get("sha")
            old_content = base64.b64decode(file_json.get("content", "")).decode("utf-8", errors="ignore")

        # حفظ نسخة احتياطية قبل التعديل للتراجع الفوري
        prop["backup_content"] = old_content
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(prop, ensure_ascii=False)}, q=f"?id=eq.{pid}")

        merged_content = f"{old_content}\n\n# --- Auto-Approved Upgrade #{pid} ---\n{new_code}\n"
        b64_updated = base64.b64encode(merged_content.encode("utf-8")).decode("utf-8")
        payload = {"message": f"Approved Evolution Upgrade #{pid}: {prop.get('title', '')}", "content": b64_updated}
        if sha:
            payload["sha"] = sha

        r_put = requests.put(url, headers=headers, json=payload, timeout=20)
        if r_put.status_code in (200, 201):
            return (
                f"✅ *تم اعتماد وتثبيت التطوير رقم {pid} بنجاح!*\n"
                f"• *الملف المحدّث:* `{target_file}`\n"
                f"• *النسخة الاحتياطية:* محفوظة بأمان.\n"
                f"↩️ *للتراجع الفوري في أي وقت اكتب:* `تراجع عن التطوير {pid}`"
            )
        return f"⚠️ تعذر التحديث على GitHub (رمز الحالة: {r_put.status_code})."
    except Exception as exc:
        return f"⚠️ حدث خطأ أثناء التثبيت: {exc}"


def rollback_upgrade(pid: int) -> str:
    if not GITHUB_TOKEN:
        return "⚠️ متغير `GITHUB_TOKEN` غير مضبوط في Render."
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{pid}")
    if not res:
        return "⚠️ لم يتم العثور على سجل التطوير."
    rec = res if isinstance(res, list) else res
    prop = json.loads(rec.get("lesson_learned", "{}"))
    backup = prop.get("backup_content")
    target_file = prop.get("target_file", "")
    if backup is None or not target_file:
        return "⚠️ لا توجد نسخة احتياطية محفوظة لهذا التطوير."

    url = f"https://github.com{GITHUB_REPO}/contents/{target_file}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r_get = requests.get(url, headers=headers, timeout=15)
    sha = r_get.json().get("sha") if r_get.status_code == 200 else None

    b64_old = base64.b64encode(backup.encode("utf-8")).decode("utf-8")
    payload = {"message": f"Rollback Upgrade #{pid}", "content": b64_old}
    if sha:
        payload["sha"] = sha
    r_put = requests.put(url, headers=headers, json=payload, timeout=20)
    if r_put.status_code in (200, 201):
        return f"↩️ *تم التراجع بنجاح واستعادة النسخة السابقة للملف `{target_file}`.*"
    return f"⚠️ تعذر التراجع (رمز الحالة: {r_put.status_code})."


def _scheduler_loop():
    admin_phone = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
    admin_cid = f"{admin_phone}@c.us" if admin_phone else ""
    last_daily_report = ""

    while True:
        try:
            now = datetime.now(RIYADH_TZ)
            # 1. فحص التذكيرات المستحقة كل دقيقة
            due_list = check_due_reminders()
            for item in due_list:
                target = item.get("cid") or admin_cid
                if target:
                    send_msg(target, f"⏰ *تذكير مجدول:*\n{item.get('text', '')}")
                    BUS.publish("scheduler.reminder_sent", {"cid": target})
            # 2. تقرير التطور الذاتي اليومي واقتراح التحسينات الساعة 09:00 صباحاً بتوقيت الرياض
            today_key = now.strftime("%Y-%m-%d")
            if now.hour == 9 and now.minute == 0 and last_daily_report != today_key:
                last_daily_report = today_key
                report = analyze_system_evolution()
                if admin_cid and report:
                    send_msg(admin_cid, report)
                    BUS.publish("scheduler.daily_report_sent", {"date": today_key})
                propose_safe_upgrade()
        except Exception as exc:
            print(f"Scheduler Loop Err: {exc}", flush=True)

        time.sleep(55)


def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    BUS.publish("scheduler.started", {"status": "active"})
    return t

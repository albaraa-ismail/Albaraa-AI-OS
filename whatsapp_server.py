import os, json, io, re, time, base64, requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from openpyxl import Workbook
from core.core_ai import sb, ai_ask, ai_ask_json, send_msg
from core.orchestrator import run_task
from core.auto_scheduler import start_scheduler, propose_safe_upgrade, get_proposal_code, approve_and_deploy_upgrade, rollback_upgrade
from security.safe_guard import safe_run, inspect_prompt_injection, apply_saudi_governance
from security.iam_gateway import IAM_GATEWAY
from security.audit_ledger import AUDIT_LEDGER
from multimodal.office_tools import make_word, make_excel, make_pptx, make_powerbi_kit, make_live_powerbi, make_kpi
from multimodal.pro_capabilities import run_pro_capability, make_pdf_report
from multimodal.media_maker import make_voice_note
from multimodal.media_reader import transcribe_voice_note, read_media_from_url
from channels.robotics_bridge import ROBOTICS_BRIDGE
from telemetry.realtime_monitor import MONITOR
from telemetry.benchmark_lab import run_benchmark_suite

app = Flask(__name__)
EXECUTOR = ThreadPoolExecutor(max_workers=6)
SEEN = set()
LAST_TASK = {}

ADMIN_PHONE = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "")))
AHMED_PHONE = "".join(filter(str.isdigit, os.environ.get("AHMED_PHONE", "")))
ALLOWED_GROUP = os.environ.get("ALLOWED_GROUP", "").strip()

_TW_CDN = "".join(["https:/", "/cdn.tailwindcss.", "com"])
_CH_CDN = "".join(["https:/", "/cdn.jsdelivr.", "net/npm/chart.js"])
_GF_CDN = "".join(["https:/", "/fonts.googleapis.", "com/css2?family=Cairo:wght@400;600;700&display=swap"])

start_scheduler()

def _mark_seen(mid: str) -> bool:
    if not mid: return False
    if mid in SEEN: return True
    if len(SEEN) > 500: SEEN.clear()
    SEEN.add(mid)
    return False

@app.route("/board/<int:bid>", methods=["GET", "POST"])
def live_board(bid):
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{bid}")
    if not res:
        return "<h2 dir='rtl'>⚠️ اللوحة غير موجودة</h2>", 404

    record = res[0] if isinstance(res, list) else res
    board = json.loads(record["lesson_learned"])
    cols = board.get("cols", ["البند", "القسم", "المحقق", "المستهدف", "الحالة"])
    rows = board.get("rows", [])
    ai_reply = ""

    if request.method == "POST":
        act = request.form.get("action")
        if act == "add":
            rows.append([request.form.get(f"c{i}", "").strip() for i in range(len(cols))])
            ai_reply = "✅ تمت إضافة السجل بنجاح."
        elif act == "edit":
            idx = int(request.form.get("idx", -1))
            if 0 <= idx < len(rows):
                rows[idx] = [request.form.get(f"e{i}", "").strip() for i in range(len(cols))]
                ai_reply = "✅ تم حفظ التعديل."
        elif act == "del":
            idx = int(request.form.get("idx", -1))
            if 0 <= idx < len(rows):
                rows.pop(idx)
                ai_reply = "🗑️ تم حذف السجل."
        elif act == "chat":
            q = request.form.get("q", "").strip()
            if q:
                prompt = (
                    f"البيانات الحالية للوحة:\n{json.dumps(board, ensure_ascii=False)}\n\n"
                    f"أمر التعديل المطلوب: {q}\n\n"
                    "نفذ التعديل بدقة على الجدول (إضافة صفوف جديدة، تعديل قيم، حذف صفوف، أو إعادة بناء البيانات).\n"
                    "أرجع JSON بهذا الهيكل الدقيق:\n"
                    '{"reply": "رسالة تأكيد قصيرة طبيعية بدون إشارة للذكاء الاصطناعي", "title": "عنوان اللوحة", "cols": [...], "rows": [[...], [...]]}'
                )
                ai_data = ai_ask_json(prompt, "أنت محلل بيانات محترف تقوم بتحديث الجداول بدقة.")
                if ai_data and isinstance(ai_data.get("rows"), list) and len(ai_data["rows"]) > 0:
                    board["title"] = ai_data.get("title", board.get("title", "لوحة التحكم"))
                    cols = ai_data.get("cols", cols)
                    rows = ai_data["rows"]
                    ai_reply = f"✅ {ai_data.get('reply', 'تم تحديث البيانات بنجاح.')}"
                else:
                    ai_reply = "⚠️ تعذر معالجة التعديل حالياً، يرجى المحاولة مرة أخرى."
        board["cols"], board["rows"] = cols, rows
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(board, ensure_ascii=False)}, q=f"?id=eq.{bid}")

    labels = [str(r[0]) if isinstance(r, list) and r else str(r) for r in rows[:12] if r]
    values = []
    for r in rows[:12]:
        num = 0
        for cell in r:
            try:
                val = float(str(cell).replace("%", "").strip())
                if val > 0:
                    num = val
                    break
            except ValueError:
                continue
            clean_html = updated.replace("```html", "").replace("```", "").strip()
            if "<html" in clean_html.lower() or "<body" in clean_html.lower() or "<div" in clean_html.lower():
                html_code = apply_saudi_governance("موقع", clean_html)
                sb("PATCH", "self_learning_logs", {"lesson_learned": html_code}, q=f"?id=eq.{sid}")
    edit_bar = """
    <div id='live-editor-bar' dir='rtl' style='position:fixed;bottom:12px;left:12px;right:12px;z-index:99999;background:rgba(15,23,42,0.95);border:1px solid #334155;padding:10px 14px;border-radius:14px;display:flex;gap:8px;align-items:center;box-shadow:0 10px 25px rgba(0,0,0,0.4);font-family:sans-serif;'>
      <form method='POST' style='display:flex;gap:8px;width:100%;margin:0;'>
        <input name='edit_req' placeholder='اكتب أي تعديل على تصميم الموقع أو ألوانه ومحتواه ليتم تطبيقه فوراً...' style='flex:1;padding:8px 12px;border-radius:8px;border:1px solid #475569;background:#020617;color:#fff;font-size:13px;' required>
        <button type='submit' style='background:#0284c7;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-weight:bold;cursor:pointer;font-size:13px;'>تحديث الصفحة</button>
        <button type='button' onclick="document.getElementById('live-editor-bar').style.display='none'" style='background:#334155;color:#cbd5e1;border:none;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:12px;'>إخفاء</button>
      </form>
    </div>
    """
    return f"{html_code}\n{edit_bar}"


@app.route("/timeline", methods=["GET"])
def performance_timeline():
    kpis = sb("GET", "telemetry_kpis", q="?order=id.desc&limit=30") or []
    logs = sb("GET", "self_learning_logs", q="?order=id.desc&limit=20") or []
    rows_html = "".join([
        f"<tr class='border-b border-slate-800'><td class='p-3'>{k.get('user_role','-')}</td><td class='p-3'>{k.get('unit_used','-')}</td><td class='p-3 text-emerald-400'>{k.get('response_time_sec',0)} ث</td><td class='p-3 text-sky-400'>{k.get('user_growth_score',95)}%</td></tr>"
        for k in kpis if isinstance(k, dict)
    ])
    notes_html = "".join([
        f"<li class='p-2 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-300'>{str(l.get('lesson_learned',''))[:140]}</li>"
        for l in logs if isinstance(l, dict) and l.get('user_role') not in ('live_board', 'live_site')
    ])
    return f"""<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>المسار الزمني لتطور الأداء</title><script src='{_TW_CDN}'></script><link href='{_GF_CDN}' rel='stylesheet'>
    <style>body{{font-family:'Cairo',sans-serif;background:#0b1120;color:#f8fafc;}}</style></head>
    <body class='p-6 max-w-6xl mx-auto'>
      <h1 class='text-2xl font-bold text-amber-400 mb-6'>📈 المسار الزمني لقياس الجودة وتطور أداء المستخدمين</h1>
      <div class='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        <div class='lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden'>
          <table class='w-full text-right'><thead class='bg-slate-950 text-slate-400 text-xs'><tr><th class='p-3'>المستخدم</th><th class='p-3'>المهمة</th><th class='p-3'>سرعة الإنجاز</th><th class='p-3'>مؤشر الجودة</th></tr></thead><tbody>{rows_html}</tbody></table>
        </div>
        <div class='bg-slate-900 border border-slate-800 rounded-2xl p-4'><h3 class='font-bold text-sky-400 mb-3'>🧠 سجل التعلم والتفضيلات</h3><ul class='space-y-2'>{notes_html}</ul></div>
      </div>
    </body></html>"""


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "audit_chain": AUDIT_LEDGER.verify_integrity()}), 200


@app.route("/api/telemetry", methods=["GET"])
def api_telemetry():
    return jsonify({"telemetry": MONITOR.snapshot(), "fleet": ROBOTICS_BRIDGE.fleet_status()}), 200


@app.route("/api/benchmark", methods=["GET"])
def api_benchmark():
    return jsonify(run_benchmark_suite()), 200


@app.route("/api/chat", methods=["POST"])
def api_web_chat():
    body = request.get_json(silent=True) or {}
    msg = str(body.get("message", "")).strip()
    uid = str(body.get("user_id", "web_guest")).strip()
    if not msg:
        return jsonify({"error": "empty_message"}), 400
    reply = run_task(f"web_{uid}", msg, "trainee", uid)
    return jsonify({"reply": reply}), 200


@app.route("/api/robotics", methods=["POST"])
def api_robotics():
    body = request.get_json(silent=True) or {}
    dev = str(body.get("device_id", "unit_01"))
    if "command" in body:
        return jsonify(ROBOTICS_BRIDGE.dispatch_command("api_operator", dev, body["command"], body.get("params"))), 200
    return jsonify(ROBOTICS_BRIDGE.register_telemetry(dev, body)), 200


@app.route("/", methods=["GET"])
def home():
    return "System Online", 200


HELP_MENU = (
    "📌 *الخدمات والقدرات المتكاملة (58 قدرة تنفيذية وحاكمة):*\n\n"
    "1️⃣ *مستندات Word وبحوث أكاديمية:* اكتب (تقرير وورد عن... أو بحث علمي عن...)\n"
    "2️⃣ *تصدير PDF رسمي:* اكتب (تقرير pdf عن...)\n"
    "3️⃣ *لوحات قيادة Excel + رسوم بيانية:* اكتب (لوحة إكسل لـ...)\n"
    "4️⃣ *عروض تقديمية PowerPoint بالصور:* اكتب (عرض بوربوينت عن...)\n"
    "5️⃣ *لوحات Power BI حية + DAX:* اكتب (لوحة باور بي اي حية لـ... أو دليل باور بي اي لـ...)\n"
    "6️⃣ *تصميم مواقع حية ورفعها على GitHub:* اكتب (صمم موقع لـ... أو ارفع على قيت هب...)\n"
    "7️⃣ *التجارة الإلكترونية (سلة/زد) والتسويق:* اكتب (خطة متجر أو وصف منتج أو حملة إعلانية لـ...)\n"
    "8️⃣ *الموارد البشرية والتوظيف:* اكتب (وصف وظيفي أو فرز سير ذاتية أو حقيبة تدريبية لـ...)\n"
    "9️⃣ *الهندسة والعقارات والمالية (ZATCA):* اكتب (جدوى عقارية أو حساب كميات أو عرض سعر ضريبي لـ...)\n"
    "🔟 *العقود والقانون السعودي والحوكمة:* اكتب (صياغة عقد أو خطاب رسمي أو محضر اجتماع لـ...)\n"
    "1️⃣1️⃣ *الصوتيات والتقارير الزمنية:* اكتب (اقرأ بصوت: النص) أو (تقرير الأداء)\n\n"
    "✨ *التخصيص والتطوير الآمن:*\n"
    "• لحفظ قاعدة دائمة لأسلوبك: ابدأ رسالتك بـ *(قاعدة: ...)* أو *(ملاحظة: ...)*\n"
    "• لتعديل آخر مخرج فوراً: اكتب *(تعديل: ملاحظتك هنا)*\n"
    "• لفحص وتطوير النظام: اكتب *(اقترح تطوير)*"
)
            clean_html = updated.replace("```html", "").replace("```", "").strip()
            if "<html" in clean_html.lower() or "<body" in clean_html.lower() or "<div" in clean_html.lower():
                html_code = apply_saudi_governance("موقع", clean_html)
                sb("PATCH", "self_learning_logs", {"lesson_learned": html_code}, q=f"?id=eq.{sid}")
    edit_bar = """
    <div id='live-editor-bar' dir='rtl' style='position:fixed;bottom:12px;left:12px;right:12px;z-index:99999;background:rgba(15,23,42,0.95);border:1px solid #334155;padding:10px 14px;border-radius:14px;display:flex;gap:8px;align-items:center;box-shadow:0 10px 25px rgba(0,0,0,0.4);font-family:sans-serif;'>
      <form method='POST' style='display:flex;gap:8px;width:100%;margin:0;'>
        <input name='edit_req' placeholder='اكتب أي تعديل على تصميم الموقع أو ألوانه ومحتواه ليتم تطبيقه فوراً...' style='flex:1;padding:8px 12px;border-radius:8px;border:1px solid #475569;background:#020617;color:#fff;font-size:13px;' required>
        <button type='submit' style='background:#0284c7;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-weight:bold;cursor:pointer;font-size:13px;'>تحديث الصفحة</button>
        <button type='button' onclick="document.getElementById('live-editor-bar').style.display='none'" style='background:#334155;color:#cbd5e1;border:none;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:12px;'>إخفاء</button>
      </form>
    </div>
    """
    return f"{html_code}\n{edit_bar}"


@app.route("/timeline", methods=["GET"])
def performance_timeline():
    kpis = sb("GET", "telemetry_kpis", q="?order=id.desc&limit=30") or []
    logs = sb("GET", "self_learning_logs", q="?order=id.desc&limit=20") or []
    rows_html = "".join([
        f"<tr class='border-b border-slate-800'><td class='p-3'>{k.get('user_role','-')}</td><td class='p-3'>{k.get('unit_used','-')}</td><td class='p-3 text-emerald-400'>{k.get('response_time_sec',0)} ث</td><td class='p-3 text-sky-400'>{k.get('user_growth_score',95)}%</td></tr>"
        for k in kpis if isinstance(k, dict)
    ])
    notes_html = "".join([
        f"<li class='p-2 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-300'>{str(l.get('lesson_learned',''))[:140]}</li>"
        for l in logs if isinstance(l, dict) and l.get('user_role') not in ('live_board', 'live_site')
    ])
    return f"""<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>المسار الزمني لتطور الأداء</title><script src='{_TW_CDN}'></script><link href='{_GF_CDN}' rel='stylesheet'>
    <style>body{{font-family:'Cairo',sans-serif;background:#0b1120;color:#f8fafc;}}</style></head>
    <body class='p-6 max-w-6xl mx-auto'>
      <h1 class='text-2xl font-bold text-amber-400 mb-6'>📈 المسار الزمني لقياس الجودة وتطور أداء المستخدمين</h1>
      <div class='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        <div class='lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden'>
          <table class='w-full text-right'><thead class='bg-slate-950 text-slate-400 text-xs'><tr><th class='p-3'>المستخدم</th><th class='p-3'>المهمة</th><th class='p-3'>سرعة الإنجاز</th><th class='p-3'>مؤشر الجودة</th></tr></thead><tbody>{rows_html}</tbody></table>
        </div>
        <div class='bg-slate-900 border border-slate-800 rounded-2xl p-4'><h3 class='font-bold text-sky-400 mb-3'>🧠 سجل التعلم والتفضيلات</h3><ul class='space-y-2'>{notes_html}</ul></div>
      </div>
    </body></html>"""


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "audit_chain": AUDIT_LEDGER.verify_integrity()}), 200


@app.route("/api/telemetry", methods=["GET"])
def api_telemetry():
    return jsonify({"telemetry": MONITOR.snapshot(), "fleet": ROBOTICS_BRIDGE.fleet_status()}), 200


@app.route("/api/benchmark", methods=["GET"])
def api_benchmark():
    return jsonify(run_benchmark_suite()), 200


@app.route("/api/chat", methods=["POST"])
def api_web_chat():
    body = request.get_json(silent=True) or {}
    msg = str(body.get("message", "")).strip()
    uid = str(body.get("user_id", "web_guest")).strip()
    if not msg:
        return jsonify({"error": "empty_message"}), 400
    reply = run_task(f"web_{uid}", msg, "trainee", uid)
    return jsonify({"reply": reply}), 200


@app.route("/api/robotics", methods=["POST"])
def api_robotics():
    body = request.get_json(silent=True) or {}
    dev = str(body.get("device_id", "unit_01"))
    if "command" in body:
        return jsonify(ROBOTICS_BRIDGE.dispatch_command("api_operator", dev, body["command"], body.get("params"))), 200
    return jsonify(ROBOTICS_BRIDGE.register_telemetry(dev, body)), 200


@app.route("/", methods=["GET"])
def home():
    return "System Online", 200


HELP_MENU = (
    "📌 *الخدمات والقدرات المتكاملة (58 قدرة تنفيذية وحاكمة):*\n\n"
    "1️⃣ *مستندات Word وبحوث أكاديمية:* اكتب (تقرير وورد عن... أو بحث علمي عن...)\n"
    "2️⃣ *تصدير PDF رسمي:* اكتب (تقرير pdf عن...)\n"
    "3️⃣ *لوحات قيادة Excel + رسوم بيانية:* اكتب (لوحة إكسل لـ...)\n"
    "4️⃣ *عروض تقديمية PowerPoint بالصور:* اكتب (عرض بوربوينت عن...)\n"
    "5️⃣ *لوحات Power BI حية + DAX:* اكتب (لوحة باور بي اي حية لـ... أو دليل باور بي اي لـ...)\n"
    "6️⃣ *تصميم مواقع حية ورفعها على GitHub:* اكتب (صمم موقع لـ... أو ارفع على قيت هب...)\n"
    "7️⃣ *التجارة الإلكترونية (سلة/زد) والتسويق:* اكتب (خطة متجر أو وصف منتج أو حملة إعلانية لـ...)\n"
    "8️⃣ *الموارد البشرية والتوظيف:* اكتب (وصف وظيفي أو فرز سير ذاتية أو حقيبة تدريبية لـ...)\n"
    "9️⃣ *الهندسة والعقارات والمالية (ZATCA):* اكتب (جدوى عقارية أو حساب كميات أو عرض سعر ضريبي لـ...)\n"
    "🔟 *العقود والقانون السعودي والحوكمة:* اكتب (صياغة عقد أو خطاب رسمي أو محضر اجتماع لـ...)\n"
    "1️⃣1️⃣ *الصوتيات والتقارير الزمنية:* اكتب (اقرأ بصوت: النص) أو (تقرير الأداء)\n\n"
    "✨ *التخصيص والتطوير الآمن:*\n"
    "• لحفظ قاعدة دائمة لأسلوبك: ابدأ رسالتك بـ *(قاعدة: ...)* أو *(ملاحظة: ...)*\n"
    "• لتعديل آخر مخرج فوراً: اكتب *(تعديل: ملاحظتك هنا)*\n"
    "• لفحص وتطوير النظام: اكتب *(اقترح تطوير)*"
)
def _is_authorized(cid: str, sender: str) -> bool:
    if ALLOWED_GROUP and (cid == ALLOWED_GROUP or ALLOWED_GROUP in cid):
        return True

    cid_digits = "".join(filter(str.isdigit, cid.split("@")[0])) if cid else ""
    sender_digits = "".join(filter(str.isdigit, sender.split("@")[0])) if sender else ""

    if ADMIN_PHONE and (cid_digits == ADMIN_PHONE or sender_digits == ADMIN_PHONE):
        return True
    if AHMED_PHONE and (cid_digits == AHMED_PHONE or sender_digits == AHMED_PHONE):
        return True

    try:
        session = IAM_GATEWAY.resolve_session(cid, sender=sender)
        return bool(session.get("authorized"))
    except Exception:
        return False


def _run_with_tip(fn, cid, task):
    fn(cid, task)
    send_msg(cid, "💡 *لتعديل هذا المخرج وإعادة إنتاجه فوراً وفق ملاحظتك، أرسل:*\n`تعديل: [اكتب التعديل المطلوب هنا]`")


def _dispatch_smart(cid: str, txt: str, sname: str):
    clean = txt.strip()
    user_tag = sname.strip() if sname and sname.strip() != "User" else "admin"
    is_admin_user = (ADMIN_PHONE and ADMIN_PHONE in "".join(filter(str.isdigit, cid.split("@")[0])))

    if any(k in clean for k in ("القائمة", "المساعدة", "الخدمات", "/help", "قدراتك", "ايش تقدر تسوي", "وش تقدر تسوي")):
        send_msg(cid, HELP_MENU)
        return

    if clean in ("تقرير الأداء", "قياس الأداء", "kpi"):
        safe_run(make_kpi, cid)
        return

    # أوامر إدارة التطور الذاتي الآمن (للمدير فقط)
    if is_admin_user:
        if clean.startswith("اقترح تطوير"):
            topic = clean.replace("اقترح تطوير", "").strip() or "تحسين الأداء وإضافة ميزة جديدة"
            send_msg(cid, "🔬 جاري البحث وتحليل السجلات لاقتراح تطوير برمجي آمن ومفحوص...")
            EXECUTOR.submit(safe_run, propose_safe_upgrade, topic)
            return
        if clean.startswith("عرض كود "):
            pid_str = "".join(filter(str.isdigit, clean))
            if pid_str:
                send_msg(cid, get_proposal_code(int(pid_str)))
            return
        if clean.startswith("اعتماد التطوير "):
            pid_str = "".join(filter(str.isdigit, clean))
            if pid_str:
                send_msg(cid, approve_and_deploy_upgrade(int(pid_str)))
            return
        if clean.startswith("تراجع عن التطوير "):
            pid_str = "".join(filter(str.isdigit, clean))
            if pid_str:
                send_msg(cid, rollback_upgrade(int(pid_str)))
            return
        if clean.startswith("رفض التطوير "):
            pid_str = "".join(filter(str.isdigit, clean))
            if pid_str:
                sb("PATCH", "self_learning_logs", {"is_active": False}, q=f"?id=eq.{pid_str}")
                send_msg(cid, f"❌ تم رفض وحذف مقترح التطوير رقم `{pid_str}`.")
            return

    for prefix in ("تعديل:", "ملاحظة:", "قاعدة:", "تغذية راجعة:"):
        if clean.startswith(prefix):
            note = clean[len(prefix):].strip()
            if not note:
                send_msg(cid, "⚠️ اكتب ملاحظتك بعد الكلمة المفتاحية، مثال:\n`تعديل: اجعل التقرير مختصراً مع إضافة أمثلة واقعية`")
                return
            sb("POST", "self_learning_logs", {"user_role": user_tag, "lesson_learned": f"[{user_tag}] {note}", "is_active": True})
            prev_task = LAST_TASK.get(cid, "")
            if prefix == "تعديل:" and prev_task:
                send_msg(cid, f"🔄 *تم حفظ ملاحظتك وتحديث أسلوب العمل!* جاري إعادة تنفيذ طلبك السابق وتطبيق التعديل فوراً:\n_{prev_task}_")
                refined_task = f"{prev_task}\n[تعديل وملاحظة إلزامية من {user_tag} يجب تطبيقها بدقة]: {note}"
                _dispatch_smart(cid, refined_task, sname)
            else:
                send_msg(cid, f"✅ *تم اعتماد القاعدة في ملفك الشخصي ({user_tag}):*\n«{note}»\n\nسيتم الالتزام بها في جميع أعمالك القادمة.")
            return

    LAST_TASK[cid] = clean

    sub_tasks = [t.strip() for t in clean.splitlines() if len(t.strip()) > 3 and not t.strip().startswith("[تعديل")]
    if len(sub_tasks) == 1 and (" و" in clean) and sum(w in clean for w in ("وورد", "اكسل", "إكسل", "بوربوينت", "باور بي", "موقع", "pdf")) >= 2:
        topic = clean.split("عن ", 1)[-1] if "عن " in clean else clean
        sub_tasks = []
        if "وورد" in clean: sub_tasks.append(f"تقرير وورد عن {topic}")
        if "pdf" in clean.lower(): sub_tasks.append(f"تقرير pdf عن {topic}")
        if any(k in clean for k in ("اكسل", "إكسل")): sub_tasks.append(f"لوحة إكسل عن {topic}")
        if "بوربوينت" in clean: sub_tasks.append(f"عرض بوربوينت عن {topic}")
        if "باور بي" in clean: sub_tasks.append(f"لوحة باور بي اي حية عن {topic}")
        if "موقع" in clean: sub_tasks.append(f"صمم موقع عن {topic}")

    for task in (sub_tasks or [clean])[:4]:
        low = task.lower()
        if any(k in low for k in ("لوحة باور بي", "باور بي اي حية", "باور بي أي حية", "live power bi", "لوحة حية")):
            EXECUTOR.submit(safe_run, make_live_powerbi, cid, task)
        elif any(k in low for k in ("دليل باور بي", "هندسة باور بي", "dax")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_powerbi_kit, cid, task)
        elif any(k in low for k in ("pdf", "بي دي اف")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_pdf_report, cid, task)
        elif any(k in low for k in ("تقرير وورد", "ملف وورد", "word", "بحث علمي", "بحث أكاديمي", "بحث اكاديمي", "دراسة علمية")) and not any(k in low for k in ("باور بي", "power bi")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_word, cid, task)
        elif any(k in low for k in ("لوحة اكسل", "لوحة إكسل", "ملف اكسل", "ملف إكسل", "excel")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_excel, cid, task)
        elif any(k in low for k in ("بوربوينت", "عرض تقديمي", "شرائح", "pptx", "powerpoint")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_pptx, cid, task)
        elif any(k in low for k in ("صمم موقع", "انشئ موقع", "أنشئ موقع", "موقع الكتروني", "موقع إلكتروني", "صفحة هبوط", "موقع ويب", "استبيان")):
            EXECUTOR.submit(safe_run, _build_live_site, cid, task)
        elif any(k in low for k in ("ارفع على قيت", "ارفع على جيت", "github", "قيت هب", "مستودع")):
            EXECUTOR.submit(safe_run, _push_to_github, cid, task)
        elif any(k in low for k in ("سلة", "زد", "متجر", "منتج", "سلة متروكة", "تسعير", "سيرة ذاتية", "توظيف", "مقابلة", "وصف وظيفي", "حقيبة تدريبية", "كميات", "مقاولات", "عقار", "جدوى عقارية", "مناقصة", "عقد", "اتفاقية", "لائحة", "محضر اجتماع", "خطاب رسمي", "فاتورة", "عرض سعر", "ضريبة", "حملة إعلانية", "سيناريو")):
            EXECUTOR.submit(safe_run, _run_with_tip, run_pro_capability, cid, task)
        elif any(k in low for k in ("اقرأ بصوت", "بصمة صوتية")):
            EXECUTOR.submit(safe_run, make_voice_note, cid, task)
        else:
            EXECUTOR.submit(safe_run, run_task, cid, task, user_tag, sname)


def _build_live_site(cid: str, task: str):
    send_msg(cid, "🌐 جاري تصميم وبرمجة الموقع وتجهيز رابط المعاينة والتعديل المباشر...")
    prompt = (
        f"صمم موقع ويب متكامل وعصري باللغة العربية (RTL) حول: {task}\n"
        "استخدم Tailwind CSS عبر CDN وخط Cairo من Google Fonts، واجعل التصميم احترافياً متجاوباً مع الجوال والحاسوب "
        "مع أقسام متكاملة وأزرار تفاعلية وصور عالية الدقة من Unsplash أو LoremFlickr.\n"
        "أرجع كود HTML الكامل فقط بدءاً من <!DOCTYPE html> وحتى </html> بدون أي مقدمات أو علامات markdown."
    )
    raw_html = ai_ask(task, prompt, mode="general", use_cache=False)
    clean_html = raw_html.replace("```html", "").replace("```", "").strip()
    if "<html" not in clean_html.lower():
        clean_html = f"<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><title>{task[:40]}</title><script src='{_TW_CDN}'></script></head><body class='bg-slate-950 text-white p-8 font-sans'>{clean_html}</body></html>"

    clean_html = apply_saudi_governance(task, clean_html)
    saved = sb("POST", "self_learning_logs", {"user_role": "live_site", "lesson_learned": clean_html, "is_active": True})
    sid = saved.get("id", 1) if isinstance(saved, list) and saved else 1
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    site_link = f"{base_url}/site/{sid}" if base_url else f"/site/{sid}"
    send_msg(cid, f"🌐 *تم تصميم وإطلاق الموقع بنجاح!*\n\n🔗 *رابط الموقع المباشر (مع أداة التعديل الفوري أسفل الصفحة):*\n{site_link}\n\n💡 يمكنك أيضاً كتابة `تعديل: [وصف التعديل]` هنا في المحادثة لإعادة بنائه.")


def _push_to_github(cid: str, task: str):
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not gh_token:
        send_msg(cid, "⚠️ للرفع التلقائي على GitHub، أضف متغير `GITHUB_TOKEN` في إعدادات Render أولاً، أو اطلب الكود وسأجهزه لك مباشرة.")
        return
    send_msg(cid, "📦 جاري تجهيز الملفات البرمجية ورفعها إلى حسابك في GitHub...")
    repo_name = f"project-{int(time.time())}"
    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    r_repo = requests.post("https://github.com", headers=headers, json={"name": repo_name, "private": False, "auto_init": True}, timeout=20)
    if r_repo.status_code not in (200, 201):
        send_msg(cid, f"⚠️ تعذر إنشاء المستودع في GitHub ({r_repo.status_code}).")
        return
    repo_info = r_repo.json()
    full_name = repo_info.get("full_name", "")
    html_url = repo_info.get("html_url", "")
    code_content = ai_ask(task, "اكتب الكود البرمجي الكامل والاحترافي لهذا المشروع بدون مقدمات أو شرح:", mode="general", use_cache=False)
    b64_code = base64.b64encode(code_content.encode("utf-8")).decode("utf-8")
    requests.put(f"https://github.com{full_name}/contents/index.html", headers=headers, json={"message": "Initial commit", "content": b64_code}, timeout=20)
    send_msg(cid, f"✅ *تم إنشاء المستودع ورفع المشروع على GitHub بنجاح:*\n{html_url}")


def _handle_media_message(cid: str, mdata: dict, sname: str):
    file_data = mdata.get("fileMessageData", {})
    dl_url = file_data.get("downloadUrl", "")
    mime = file_data.get("mimeType", "")
    caption = file_data.get("caption", "").strip()
    if not dl_url:
        return
    if caption:
        sec_check = inspect_prompt_injection(caption, cid)
        if not sec_check.get("is_safe"):
            send_msg(cid, "🛡️ تم حظر الطلب لمخالفته ضوابط الحماية والحوكمة.")
            return
    if mime.startswith("audio/"):
        transcript = transcribe_voice_note(dl_url)
        if transcript:
            send_msg(cid, f"🎙 *تم تفريغ الرسالة الصوتية:*\n«{transcript}»")
            _dispatch_smart(cid, transcript, sname)
        else:
            send_msg(cid, "⚠️ تعذر فهم الرسالة الصوتية، يرجى إعادة الإرسال.")
    else:
        analysis = read_media_from_url(dl_url, mime, caption)
        if caption and any(k in caption.lower() for k in ("وورد", "اكسل", "إكسل", "بوربوينت", "باور بي", "pdf", "تقرير", "لوحة", "لخص", "بحث", "صمم", "حلل")):
            _dispatch_smart(cid, f"{caption}\n\nالبيانات المستخرجة من المرفق:\n{analysis}", sname)
        else:
            send_msg(cid, analysis)


@app.route("/whatsapp-webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    wtype = data.get("typeWebhook", "")
    if wtype not in ("incomingMessageReceived", "outgoingMessageReceived"):
        return jsonify({"status": "ignored"}), 200

    mid = data.get("idMessage", "")
    if _mark_seen(mid):
        return jsonify({"status": "dup"}), 200

    sdata = data.get("senderData", {})
    cid = sdata.get("chatId", "")
    sender = sdata.get("sender", "")

    if not _is_authorized(cid, sender):
        print(f"BLOCKED: type={wtype} | cid={cid} | sender={sender}", flush=True)
        return jsonify({"status": "unauthorized"}), 200

    mdata = data.get("messageData", {})
    sname = sdata.get("senderName", "User")

    if mdata.get("typeMessage") in ("audioMessage", "imageMessage", "documentMessage"):
        EXECUTOR.submit(safe_run, _handle_media_message, cid, mdata, sname)
        return jsonify({"status": "media_queued"}), 200

    txt = (
        mdata.get("textMessageData", {}).get("textMessage")
        or mdata.get("extendedTextMessageData", {}).get("text")
        or ""
    ).strip()

    bot_prefixes = ("🔍", "⚙️", "🛡️", "📑", "🌐", "🚀", "💻", "⚠", "✅", "🤖", "📊", "📄", "📽️", "👥", "💡", "🧠", "🎙", "📚", "🔄", "📌", "📦", "🛍️", "🏗️", "⚖️", "🧾", "🔬", "❌", "↩️")
    if txt and cid and not any(txt.startswith(p) for p in bot_prefixes):
        sec_check = inspect_prompt_injection(txt, cid)
        if not sec_check.get("is_safe"):
            print(f"SECURITY BLOCK [{sec_check.get('matched_rule')}]: {cid}", flush=True)
            send_msg(cid, "🛡️ تم حظر هذا الطلب لمخالفته ضوابط الأمن السيبراني والحوكمة.")
            return jsonify({"status": "security_blocked"}), 200

        print(f"IN: {wtype} | CID: {cid} | MSG: {txt[:25]}", flush=True)
        EXECUTOR.submit(_dispatch_smart, cid, txt, sname)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

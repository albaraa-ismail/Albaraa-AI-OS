import io
import os
import json
import time
import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional
import requests
from flask import Flask, jsonify, request, send_file
from openpyxl import Workbook

from channels.robotics_bridge import ROBOTICS_BRIDGE
from core.auto_scheduler import (
    approve_and_deploy_upgrade,
    get_proposal_code,
    propose_safe_upgrade,
    rollback_upgrade,
    start_scheduler,
)
from core.config import ADMIN_PHONE, ALLOWED_GROUP, GITHUB_API, GITHUB_TOKEN, PARTNER_PHONE, RENDER_URL
from core.core_ai import ai_ask, ai_ask_json, ai_generate_image, sb
from core.orchestrator import run_task, send_msg
from multimodal.media_maker import make_voice_note
from multimodal.media_reader import read_media_from_url, transcribe_voice_note
from multimodal.office_tools import make_excel, make_kpi, make_live_powerbi, make_powerbi_kit, make_pptx, make_word
from multimodal.pro_capabilities import make_pdf_report, run_pro_capability
from security.audit_ledger import AUDIT_LEDGER
from security.iam_gateway import IAM_GATEWAY
from security.safe_guard import apply_saudi_governance, inspect_prompt_injection, safe_run
from telemetry.benchmark_lab import run_benchmark_suite
from telemetry.realtime_monitor import MONITOR

AHMED_PHONE = os.environ.get("AHMED_PHONE", PARTNER_PHONE or "")
app = Flask(__name__)
EXECUTOR = ThreadPoolExecutor(max_workers=6)
SEEN: set[str] = set()
LAST_TASK: dict[str, str] = {}

def _cdn(*parts: str) -> str:
    return "https" + ":" + "//" + "".join(parts)

TW_CDN = _cdn("cdn.", "tailwindcss.com")
CH_CDN = _cdn("cdn.", "jsdelivr.net", "/npm/chart.js")
GF_CDN = _cdn("fonts.", "googleapis.com", "/css2?family=Cairo:wght@400;600;700&display=swap")
start_scheduler()

def _mark_seen(mid: str) -> bool:
    if not mid:
        return False
    if mid in SEEN:
        return True
    if len(SEEN) > 500:
        SEEN.clear()
    SEEN.add(mid)
    return False

def _get_record(record_id: int) -> Optional[dict[str, Any]]:
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{record_id}")
    rec = next(iter(res), None) if isinstance(res, list) else res
    return rec if isinstance(rec, dict) else None

def _handle_board_post(board: dict[str, Any], cols: list[str], rows: list[list[Any]]) -> tuple[list[str], list[list[Any]], str]:
    act = request.form.get("action")
    try:
        idx = int(request.form.get("idx", -1))
    except ValueError:
        idx = -1
    if act == "add":
        rows.append([request.form.get(f"c{i}", "").strip() for i in range(len(cols))])
        return cols, rows, "✅ تمت إضافة السجل بنجاح."
    if act == "edit" and 0 <= idx < len(rows):
        rows[idx] = [request.form.get(f"e{i}", "").strip() for i in range(len(cols))]
        return cols, rows, "✅ تم حفظ التعديل."
    if act == "del" and 0 <= idx < len(rows):
        rows.pop(idx)
        return cols, rows, "🗑️ تم حذف السجل."
    if act == "chat" and (q := request.form.get("q", "").strip()):
        prompt = (
            f"البيانات الحالية للوحة:\n{json.dumps(board, ensure_ascii=False)}\n\n"
            f"أمر التعديل المطلوب: {q}\n\n"
            "نفذ التعديل بدقة على الجدول وأرجع JSON فقط بهذا الهيكل:\n"
            '{"reply": "رسالة تأكيد قصيرة طبيعية", "title": "عنوان اللوحة", "cols": [...], "rows": [[...]]}'
        )
        ai_data = ai_ask_json(prompt, "أنت محلل بيانات محترف تقوم بتحديث الجداول بدقة.")
        if ai_data and isinstance(ai_data.get("rows"), list) and ai_data["rows"]:
            board["title"] = ai_data.get("title", board.get("title", "لوحة التحكم"))
            return ai_data.get("cols", cols), ai_data["rows"], f"✅ {ai_data.get('reply', 'تم تحديث البيانات بنجاح.')}"
        return cols, rows, "⚠️ تعذر معالجة التعديل حالياً، يرجى المحاولة مرة أخرى."
    return cols, rows, ""

def _extract_chart_metrics(rows: list[list[Any]]) -> tuple[list[str], list[float], float, float]:
    labels = [str(next(iter(r), "")) for r in rows[:12] if r]
    values: list[float] = []
    for r in rows[:12]:
        num = 0.0
        for cell in r:
            try:
                val = float(str(cell).replace("%", "").strip())
                if val > 0:
                    num = val
                    break
            except ValueError:
                continue
        values.append(num)
    avg_val = round(sum(values) / len(values), 1) if values else 0.0
    max_val = max(values) if values else 0.0
    return labels, values, avg_val, max_val
@app.route("/board/<int:bid>", methods=["GET", "POST"])
def live_board(bid: int):
    record = _get_record(bid)
    if not record:
        return "<h2 dir='rtl'>⚠️ اللوحة غير موجودة</h2>", 404

    board = json.loads(record["lesson_learned"])
    cols = board.get("cols", ["البند", "القسم", "المحقق", "المستهدف", "الحالة"])
    rows = board.get("rows", [])
    ai_reply = ""

    if request.method == "POST":
        cols, rows, ai_reply = _handle_board_post(board, cols, rows)
        board["cols"], board["rows"] = cols, rows
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(board, ensure_ascii=False)}, q=f"?id=eq.{bid}")

    labels, values, avg_val, max_val = _extract_chart_metrics(rows)
    title = board.get("title", "لوحة القيادة الحية")

    add_inputs = "".join(
        f"<div class='flex-1 min-w-[140px]'><label class='text-xs text-slate-400 block mb-1'>{c}</label>"
        f"<input name='c{i}' class='w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white' required></div>"
        for i, c in enumerate(cols)
    )
    rows_html = "".join(
        f"<tr class='border-b border-slate-800 hover:bg-slate-800/40'><form method='POST'>"
        f"<input type='hidden' name='idx' value='{r_i}'>"
        + "".join(
            f"<td class='p-2'><input name='e{c_i}' value='{r[c_i] if c_i < len(r) else ''}' "
            f"class='w-full bg-slate-900/70 border border-slate-700/70 rounded px-2 py-1 text-sm text-slate-100'></td>"
            for c_i in range(len(cols))
        )
        + "<td class='p-2 flex gap-1'><button name='action' value='edit' class='bg-emerald-600 hover:bg-emerald-500 px-2.5 py-1 rounded text-xs'>💾</button>"
        "<button name='action' value='del' class='bg-rose-600 hover:bg-rose-500 px-2.5 py-1 rounded text-xs'>🗑</button></td></form></tr>"
        for r_i, r in enumerate(rows)
    )
    headers_html = "".join(f"<th class='p-3 border-b border-slate-800'>{c}</th>" for c in cols)
    reply_banner = f"<div class='mt-3 p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-sm text-sky-300'>{ai_reply}</div>" if ai_reply else ""

    return f"""<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>{title}</title><script src='{TW_CDN}'></script><script src='{CH_CDN}'></script><link href='{GF_CDN}' rel='stylesheet'>
    <style>body{{font-family:'Cairo',sans-serif;background:#0b1120;color:#f8fafc;user-select:none}}input,textarea{{user-select:text}}</style></head>
    <body oncontextmenu='return false;' class='p-4 md:p-8 max-w-7xl mx-auto'>
      <div class='flex flex-wrap justify-between items-center gap-4 mb-6 bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl'>
        <div><span class='text-xs font-semibold px-2.5 py-1 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20'>لوحة بيانات تفاعلية</span>
        <h1 class='text-2xl font-bold mt-2 text-white'>📊 {title}</h1></div>
        <a href='/board/{bid}/export' class='bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-2.5 rounded-xl text-sm shadow transition'>📥 تصدير Excel</a>
      </div>
      <div class='grid grid-cols-1 md:grid-cols-3 gap-4 mb-6'>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>إجمالي السجلات</p><p class='text-3xl font-bold text-sky-400 mt-1'>{len(rows)}</p></div>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>متوسط المؤشر الرقمي</p><p class='text-3xl font-bold text-emerald-400 mt-1'>{avg_val}</p></div>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>أعلى قيمة مسجلة</p><p class='text-3xl font-bold text-amber-400 mt-1'>{max_val}</p></div>
      </div>
      <div class='bg-gradient-to-l from-slate-900 to-indigo-950/40 border border-indigo-500/30 p-5 rounded-2xl mb-6 shadow-lg'>
        <form method='POST' class='flex flex-col md:flex-row gap-3'>
          <input name='q' placeholder='اكتب التعديل المطلوب على الجدول (مثال: أضف 5 موظفين جدد لقسم التقنية أو عدل إنجاز أحمد إلى 98%)...' class='flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500' required>
          <button name='action' value='chat' class='bg-sky-600 hover:bg-sky-500 text-white font-bold px-6 py-3 rounded-xl text-sm transition'>⚡ تطبيق التعديل</button>
        </form>{reply_banner}
      </div>
      <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl mb-6'><h3 class='text-sm font-bold text-slate-300 mb-3'>📈 التحليل البصري الفوري</h3><div class='h-64'><canvas id='kpiChart'></canvas></div></div>
      <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl mb-6'><h3 class='text-sm font-bold text-slate-300 mb-3'>➕ إضافة سجل يدوي</h3><form method='POST' class='flex flex-wrap items-end gap-3'>{add_inputs}<button name='action' value='add' class='bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-5 py-2 rounded-lg text-sm'>حفظ</button></form></div>
      <div class='bg-slate-900 border border-slate-800 rounded-2xl overflow-x-auto'>
        <table class='w-full text-right border-collapse'><thead><tr class='bg-slate-950 text-slate-300 text-xs uppercase'>{headers_html}<th class='p-3 border-b border-slate-800'>تحكم</th></tr></thead><tbody>{rows_html}</tbody></table>
      </div>
      <script>
        document.addEventListener('keydown', e => {{ if (e.ctrlKey && ['u','s','c'].includes(e.key.toLowerCase())) e.preventDefault(); }});
        new Chart(document.getElementById('kpiChart'), {{
          type: 'bar',
          data: {{ labels: {json.dumps(labels, ensure_ascii=False)}, datasets: [{{ label: 'القيمة / المؤشر', data: {json.dumps(values)}, backgroundColor: 'rgba(56,189,248,0.75)', borderColor: '#38bdf8', borderWidth: 1, borderRadius: 6 }}] }},
          options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }}, scales: {{ x: {{ ticks: {{ color: '#94a3b8' }} }}, y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }} }} }}
        }});
      </script>
    </body></html>"""

@app.route("/board/<int:bid>/export")
def export_board(bid: int):
    record = _get_record(bid)
    if not record:
        return "Not Found", 404
    board = json.loads(record["lesson_learned"])
    wb = Workbook()
    ws = wb.active
    ws.sheet_view.rightToLeft = True
    ws.append(board.get("cols", []))
    for r in board.get("rows", []):
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"Dashboard_{bid}.xlsx")

@app.route("/site/<int:sid>", methods=["GET", "POST"])
def live_site(sid: int):
    record = _get_record(sid)
    if not record:
        return "<h2 dir='rtl'>⚠️ الصفحة غير موجودة</h2>", 404

    html_code = record.get("lesson_learned", "")
    if request.method == "POST" and (edit_req := request.form.get("edit_req", "").strip()):
        updated = ai_ask(
            f"الكود الحالي للصفحة:\n{html_code}\n\nالتعديل المطلوب:\n{edit_req}",
            "أنت مطور واجهات ويب محترف. عدل كود HTML/CSS/JS التالي بناء على طلب المستخدم وأرجع الكود الكامل الصالح للعرض مباشرة بدون أي مقدمات أو علامات markdown.",
            mode="coding",
            use_cache=False,
        )
        clean_html = updated.replace("```html", "").replace("```", "").strip()
        if any(tag in clean_html.lower() for tag in ("<html", "<body", "<div")):
            html_code = apply_saudi_governance("موقع", clean_html)
            sb("PATCH", "self_learning_logs", {"lesson_learned": html_code}, q=f"?id=eq.{sid}")

    edit_bar = (
        "<div id='live-editor-bar' dir='rtl' style='position:fixed;bottom:12px;left:12px;right:12px;z-index:99999;"
        "background:rgba(15,23,42,0.95);border:1px solid #334155;padding:10px 14px;border-radius:14px;display:flex;gap:8px;align-items:center;"
        "box-shadow:0 10px 25px rgba(0,0,0,0.4);font-family:sans-serif;'>"
        "<form method='POST' style='display:flex;gap:8px;width:100%;margin:0;'>"
        "<input name='edit_req' placeholder='اكتب أي تعديل على تصميم الموقع أو ألوانه ومحتواه ليتم تطبيقه فورا...' "
        "style='flex:1;padding:8px 12px;border-radius:8px;border:1px solid #475569;background:#020617;color:#fff;font-size:13px;' required>"
        "<button type='submit' style='background:#0284c7;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-weight:bold;cursor:pointer;font-size:13px;'>تحديث الصفحة</button>"
        "<button type='button' onclick=\"document.getElementById('live-editor-bar').style.display='none'\" "
        "style='background:#334155;color:#cbd5e1;border:none;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:12px;'>إخفاء</button>"
        "</form></div>"
    )
    return f"{html_code}\n{edit_bar}"

@app.route("/timeline", methods=["GET"])
def performance_timeline():
    kpis = sb("GET", "telemetry_kpis", q="?order=id.desc&limit=30") or []
    logs = sb("GET", "self_learning_logs", q="?order=id.desc&limit=20") or []
    rows_html = "".join(
        f"<tr class='border-b border-slate-800'><td class='p-3'>{k.get('user_role','-')}</td><td class='p-3'>{k.get('unit_used','-')}</td>"
        f"<td class='p-3 text-emerald-400'>{k.get('response_time_sec',0)} ث</td><td class='p-3 text-sky-400'>{k.get('user_growth_score',95)}%</td></tr>"
        for k in kpis if isinstance(k, dict)
    )
    notes_html = "".join(
        f"<li class='p-2 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-300'>{str(l.get('lesson_learned',''))[:140]}</li>"
        for l in logs if isinstance(l, dict) and l.get("user_role") not in ("live_board", "live_site")
    )
    return f"""<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>المسار الزمني لتطور الأداء</title><script src='{TW_CDN}'></script><link href='{GF_CDN}' rel='stylesheet'>
    <style>body{{font-family:'Cairo',sans-serif;background:#0b1120;color:#f8fafc}}</style></head>
    <body class='p-6 max-w-6xl mx-auto'><h1 class='text-2xl font-bold text-amber-400 mb-6'>📈 المسار الزمني لقياس الجودة وتطور أداء المستخدمين</h1>
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
    return (jsonify({"reply": run_task(f"web_{uid}", msg, "trainee", uid, notify_whatsapp=False)}), 200) if msg else (jsonify({"error": "empty_message"}), 400)

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
    "1️⃣1️⃣ *الصوتيات والصور والتقارير الزمنية:* اكتب (ارسم... أو اقرأ بصوت: النص أو لوحة قياس الإنتاجية)\n\n"
    "✨ *التخصيص والتطوير الآمن:*\n"
    "• لحفظ قاعدة دائمة لأسلوبك: ابدأ رسالتك بـ *(قاعدة: ...)* أو *(ملاحظة: ...)*\n"
    "• لتعديل آخر مخرج فوراً: اكتب *(تعديل: ملاحظتك هنا)*\n"
    "• لفحص وتطوير النظام: اكتب *(اقترح تطوير)*"
)

def _digits(jid: str) -> str:
    return "".join(filter(str.isdigit, str(jid or "").split("@", 1)))
def _is_owner(cid: str, sender: str) -> bool:
    owner = ADMIN_PHONE or "966575475336"
    c_num, s_num = _digits(cid), _digits(sender)
    return any(n == owner or (len(owner) >= 9 and n.endswith(owner[-9:])) for n in (c_num, s_num) if n)

def _is_in_allowed_group(cid: str) -> bool:
    return bool(ALLOWED_GROUP and cid and (cid == ALLOWED_GROUP or ALLOWED_GROUP in cid))

def _is_authorized(cid: str, sender: str) -> bool:
    if not cid:
        return False
    if _is_in_allowed_group(cid):
        ahmed_digits = _digits(AHMED_PHONE)
        s_num = _digits(sender)
        is_ahmed = bool(ahmed_digits and s_num and (s_num == ahmed_digits or s_num.endswith(ahmed_digits[-9:])))
        return _is_owner(cid, sender) or is_ahmed
    if "@g.us" not in cid and _is_owner(cid, sender):
        return True
    return False

def _run_with_tip(fn, cid: str, task: str) -> None:
    fn(cid, task)
    send_msg(cid, "💡 *لتعديل هذا المخرج وإعادة إنتاجه فوراً وفق ملاحظتك، أرسل:*\n`تعديل: [اكتب التعديل المطلوب هنا]`")

def _handle_admin_commands(cid: str, clean: str) -> bool:
    if clean.startswith("اقترح تطوير"):
        topic = clean.replace("اقترح تطوير", "").strip() or "تحسين الأداء وإضافة ميزة جديدة"
        send_msg(cid, "🔬 جاري البحث وتحليل السجلات لاقتراح تطوير برمجي آمن ومفحوص...")
        EXECUTOR.submit(safe_run, propose_safe_upgrade, topic)
        return True

    pid_str = "".join(filter(str.isdigit, clean))
    actions = {
        "عرض كود ": lambda pid: send_msg(cid, get_proposal_code(pid)),
        "اعتماد التطوير ": lambda pid: send_msg(cid, approve_and_deploy_upgrade(pid)),
        "تراجع عن التطوير ": lambda pid: send_msg(cid, rollback_upgrade(pid)),
        "رفض التطوير ": lambda pid: (
            sb("PATCH", "self_learning_logs", {"is_active": False}, q=f"?id=eq.{pid}"),
            send_msg(cid, f"❌ تم رفض وحذف مقترح التطوير رقم `{pid}`."),
        ),
    }
    for prefix, handler in actions.items():
        if clean.startswith(prefix):
            if pid_str:
                handler(int(pid_str))
            return True
    return False

def _dispatch_smart(cid: str, txt: str, sname: str, is_admin: bool = False, from_voice: bool = False) -> None:
    clean = txt.strip()
    user_tag = sname.strip() if sname and sname.strip() != "User" else ("admin" if is_admin else "partner")

    if any(k in clean for k in ("القائمة", "المساعدة", "الخدمات", "/help", "قدراتك", "ايش تقدر تسوي", "وش تقدر تسوي")):
        send_msg(cid, HELP_MENU)
        return

    if is_admin and _handle_admin_commands(cid, clean):
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
                _dispatch_smart(cid, f"{prev_task}\n[تعديل وملاحظة إلزامية من {user_tag} يجب تطبيقها بدقة]: {note}", sname, is_admin)
            else:
                send_msg(cid, f"✅ *تم اعتماد القاعدة في ملفك الشخصي ({user_tag}):*\n«{note}»\n\nسيتم الالتزام بها في جميع أعمالك القادمة.")
            return

    LAST_TASK[cid] = clean
    low_clean = clean.lower()

    explicit_doc = any(low_clean.startswith(p) for p in ("صمم", "انشئ", "أنشئ", "سوي", "اعمل", "اكتب تقرير", "ملف وورد", "تقرير وورد", "لوحة", "عرض"))
    if from_voice and not explicit_doc:
        EXECUTOR.submit(safe_run, run_task, cid, clean, user_tag, sname)
        return

    sub_tasks = [t.strip() for t in clean.splitlines() if len(t.strip()) > 3 and not t.strip().startswith("[تعديل")]
    multi_map = [
        (("وورد",), "تقرير وورد"),
        (("pdf",), "تقرير pdf"),
        (("اكسل", "إكسل"), "لوحة إكسل"),
        (("بوربوينت",), "عرض بوربوينت"),
        (("باور بي",), "لوحة باور بي اي حية"),
        (("موقع",), "صمم موقع"),
    ]
    if len(sub_tasks) == 1 and (" و" in clean) and sum(any(k in low_clean for k in keys) for keys, _ in multi_map) >= 2:
        topic = clean.split("عن ", 1)[-1] if "عن " in clean else clean
        sub_tasks = [f"{prefix} عن {topic}" for keys, prefix in multi_map if any(k in low_clean for k in keys)]

    task_routes = [
        (("ارسم", "صورة ل", "صوره ل", "شعار", "غلاف", "تصميم بصري"), lambda t: safe_run(_send_generated_image, cid, t)),
        (("لوحة حية", "لوحة تحكم", "قياس الإنتاجية", "قياس الانتاجية", "موقع للوحة", "موقع لوحة", "لوحة إنتاجية", "لوحة انتاجية", "لوحة باور بي", "باور بي اي حية", "live power bi"), lambda t: safe_run(make_live_powerbi, cid, t)),
        (("تقرير الأداء", "قياس الأداء", "kpi"), lambda t: safe_run(make_kpi, cid)),
        (("دليل باور بي", "هندسة باور بي", "dax"), lambda t: safe_run(_run_with_tip, make_powerbi_kit, cid, t)),
        (("pdf", "بي دي اف"), lambda t: safe_run(_run_with_tip, make_pdf_report, cid, t)),
        (("لوحة اكسل", "لوحة إكسل", "ملف اكسل", "ملف إكسل", "excel"), lambda t: safe_run(_run_with_tip, make_excel, cid, t)),
        (("بوربوينت", "عرض تقديمي", "شرائح", "pptx", "powerpoint"), lambda t: safe_run(_run_with_tip, make_pptx, cid, t)),
        (("صمم موقع", "انشئ موقع", "أنشئ موقع", "موقع الكتروني", "موقع إلكتروني", "صفحة هبوط", "موقع ويب", "استبيان"), lambda t: safe_run(_build_live_site, cid, t)),
        (("ارفع على قيت", "ارفع على جيت", "github", "قيت هب", "مستودع"), lambda t: safe_run(_push_to_github, cid, t)),
        (("اقرأ بصوت", "بصمة صوتية"), lambda t: safe_run(make_voice_note, cid, t)),
        (("سلة", "زد", "متجر", "منتج", "سلة متروكة", "تسعير", "سيرة ذاتية", "توظيف", "مقابلة", "وصف وظيفي", "حقيبة تدريبية", "كميات", "مقاولات", "عقار", "جدوى عقارية", "مناقصة", "عقد", "اتفاقية", "لائحة", "محضر اجتماع", "خطاب رسمي", "فاتورة", "عرض سعر", "ضريبة", "حملة إعلانية", "سيناريو"), lambda t: safe_run(_run_with_tip, run_pro_capability, cid, t)),
    ]
    for task in (sub_tasks or [clean])[:4]:
        low = task.lower()
        if any(k in low for k in ("تقرير وورد", "ملف وورد", "word", "بحث علمي", "بحث أكاديمي", "بحث اكاديمي", "دراسة علمية")) and not any(k in low for k in ("باور بي", "power bi", "لوحة")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_word, cid, task)
            continue

        matched_handler = next((handler for keys, handler in task_routes if any(k in low for k in keys)), None)
        if matched_handler:
            EXECUTOR.submit(matched_handler, task)
        else:
            EXECUTOR.submit(safe_run, run_task, cid, task, user_tag, sname)

def _send_generated_image(cid: str, task: str) -> None:
    send_msg(cid, "🎨 جاري رسم وتصميم الصورة بأعلى دقة...")
    img_bytes = ai_generate_image(task)
    if not img_bytes:
        send_msg(cid, "⚠️ تعذر توليد الصورة حالياً، يرجى المحاولة بوصف مختلف.")
        return
    gid = os.environ.get("GREEN_API_ID") or os.environ.get("GREEN_ID", "")
    gtok = os.environ.get("GREEN_API_TOKEN") or os.environ.get("GREEN_TOKEN", "")
    gurl = os.environ.get("GREEN_API_URL") or os.environ.get("GREEN_BASE") or "".join(["https://", "api.", "green-api.com"])
    url = f"{gurl}/waInstance{gid}/sendFileByUpload/{gtok}"
    requests.post(
        url,
        data={"chatId": cid, "caption": f"🎨 تم التصميم: {task[:80]}"},
        files={"file": ("design.png", img_bytes, "image/png")},
        timeout=30,
    )

def _build_live_site(cid: str, task: str) -> None:
    send_msg(cid, "🌐 جاري تصميم وبرمجة الموقع وتجهيز رابط المعاينة والتعديل المباشر...")
    prompt = (
        f"صمم موقع ويب متكامل وعصري باللغة العربية (RTL) حول: {task}\n"
        "استخدم Tailwind CSS عبر CDN وخط Cairo من Google Fonts، واجعل التصميم احترافيا متجاوبا مع الجوال والحاسوب "
        "مع أقسام متكاملة وأزرار تفاعلية وصور عالية الدقة من Unsplash أو LoremFlickr.\n"
        "أرجع كود HTML الكامل فقط بدءا من <!DOCTYPE html> وحتى </html> بدون أي مقدمات أو علامات markdown."
    )
    clean_html = ai_ask(task, prompt, mode="coding", use_cache=False).replace("```html", "").replace("```", "").strip()
    if "<html" not in clean_html.lower():
        clean_html = f"<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><title>{task[:40]}</title><script src='{TW_CDN}'></script></head><body class='bg-slate-950 text-white p-8 font-sans'>{clean_html}</body></html>"

    clean_html = apply_saudi_governance(task, clean_html)
    saved = sb("POST", "self_learning_logs", {"user_role": "live_site", "lesson_learned": clean_html, "is_active": True})
    rec = next(iter(saved), {}) if isinstance(saved, list) else (saved or {})
    sid = rec.get("id", 1) if isinstance(rec, dict) else 1
    site_link = f"{RENDER_URL}/site/{sid}" if RENDER_URL else f"/site/{sid}"
    send_msg(cid, f"🌐 *تم تصميم وإطلاق الموقع بنجاح!*\n\n🔗 *رابط الموقع المباشر (مع أداة التعديل الفوري أسفل الصفحة):*\n{site_link}\n\n💡 يمكنك أيضا كتابة `تعديل: [وصف التعديل]` هنا في المحادثة لإعادة بنائه.")

def _push_to_github(cid: str, task: str) -> None:
    if not GITHUB_TOKEN:
        send_msg(cid, "⚠️ للرفع التلقائي على GitHub، أضف متغير `GITHUB_TOKEN` في إعدادات Render أولا، أو اطلب الكود وسأجهزه لك مباشرة.")
        return

    send_msg(cid, "📦 جاري تجهيز الملفات البرمجية ورفعها إلى حسابك في GitHub...")
    repo_name = f"project-{int(time.time())}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r_repo = requests.post(f"{GITHUB_API}/user/repos", headers=headers, json={"name": repo_name, "private": False, "auto_init": True}, timeout=15)
    if r_repo.status_code not in (200, 201):
        send_msg(cid, f"⚠️ تعذر إنشاء المستودع في GitHub ({r_repo.status_code}).")
        return

    repo_info = r_repo.json()
    full_name, html_url = repo_info.get("full_name", ""), repo_info.get("html_url", "")
    code_content = ai_ask(task, "اكتب الكود البرمجي الكامل والاحترافي لهذا المشروع بدون مقدمات أو شرح:", mode="coding", use_cache=False)
    b64_code = base64.b64encode(code_content.encode("utf-8")).decode("utf-8")
    requests.put(f"{GITHUB_API}/repos/{full_name}/contents/index.html", headers=headers, json={"message": "Initial commit", "content": b64_code}, timeout=15)
    send_msg(cid, f"✅ *تم إنشاء المستودع ورفع المشروع على GitHub بنجاح:*\n{html_url}")

BOT_PREFIXES = (
    "🔍", "⚙️", "🛡️", "📑", "🌐", "🚀", "💻", "⚠", "✅", "🤖", "📊", "📄", "📽️", "🎨",
    "👥", "💡", "🧠", "🎙", "📚", "🔄", "📌", "📦", "🛍️", "🏗️", "⚖️", "🧾", "🔬", "❌", "↩️",
)
VALID_WEBHOOKS = {"incomingMessageReceived", "outgoingMessageReceived"}
MEDIA_TYPES = {"audioMessage", "imageMessage", "documentMessage"}
EXPORT_KEYWORDS = ("وورد", "اكسل", "إكسل", "بوربوينت", "باور بي", "pdf", "تقرير", "لوحة", "لخص")

def _handle_media_message(cid: str, mdata: dict[str, Any], sname: str, is_admin: bool = False) -> None:
    file_data = mdata.get("fileMessageData", {})
    dl_url = file_data.get("downloadUrl", "")
    if not dl_url:
        return
    mime = file_data.get("mimeType", "")
    caption = file_data.get("caption", "").strip()

    if caption and not inspect_prompt_injection(caption, cid).get("is_safe"):
        send_msg(cid, "🛡️ تم حظر الطلب لمخالفته ضوابط الحماية والحوكمة.")
        return

    if mime.startswith("audio/"):
        if transcript := transcribe_voice_note(dl_url):
            send_msg(cid, f"🎙 *تم تفريغ الرسالة الصوتية:*\n«{transcript}»")
            _dispatch_smart(cid, transcript, sname, is_admin, from_voice=True)
        else:
            send_msg(cid, "⚠️ تعذر فهم الرسالة الصوتية، يرجى إعادة الإرسال.")
        return

    analysis = read_media_from_url(dl_url, mime, caption)
    if caption and any(k in caption.lower() for k in EXPORT_KEYWORDS):
        _dispatch_smart(cid, f"{caption}\n\nالبيانات المستخرجة من المرفق:\n{analysis}", sname, is_admin)
    else:
        send_msg(cid, analysis)

@app.route("/whatsapp-webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    wtype = data.get("typeWebhook", "")
    if wtype not in VALID_WEBHOOKS or _mark_seen(data.get("idMessage", "")):
        return jsonify({"status": "ignored"}), 200

    sdata = data.get("senderData") or {}
    cid, sender = sdata.get("chatId", ""), sdata.get("sender", "")
    if not _is_authorized(cid, sender):
        return jsonify({"status": "unauthorized"}), 200

    is_admin = _is_owner(cid, sender)
    mdata = data.get("messageData") or {}
    sname = sdata.get("senderName", "User")

    if mdata.get("typeMessage") in MEDIA_TYPES:
        EXECUTOR.submit(safe_run, _handle_media_message, cid, mdata, sname, is_admin)
        return jsonify({"status": "media_queued"}), 200

    txt_data = mdata.get("textMessageData") or {}
    ext_data = mdata.get("extendedTextMessageData") or {}
    txt = str(txt_data.get("textMessage") or ext_data.get("text") or "").strip()

    if txt and cid and not txt.startswith(BOT_PREFIXES):
        if not inspect_prompt_injection(txt, cid).get("is_safe"):
            send_msg(cid, "🛡️ تم حظر هذا الطلب لمخالفته ضوابط الأمن السيبراني والحوكمة.")
            return jsonify({"status": "security_blocked"}), 200

        EXECUTOR.submit(_dispatch_smart, cid, txt, sname, is_admin)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

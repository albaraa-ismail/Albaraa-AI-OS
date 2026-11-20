import os, json, io, re, requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from openpyxl import Workbook
from core.core_ai import sb, ai_ask, ai_ask_json, send_msg
from core.orchestrator import run_task
from core.auto_scheduler import start_scheduler
from security.safe_guard import safe_run
from security.iam_gateway import IAM_GATEWAY
from security.audit_ledger import AUDIT_LEDGER
from multimodal.office_tools import make_word, make_excel, make_pptx, make_powerbi_kit, make_live_powerbi, make_kpi
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
    values.append(num)
    avg_val = round(sum(values) / len(values), 1) if values else 0
    max_val = max(values) if values else 0
    add_inputs = "".join([f"<div class='flex-1 min-w-[140px]'><label class='text-xs text-slate-400 block mb-1'>{c}</label><input name='c{i}' class='w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white' required></div>" for i, c in enumerate(cols)])
    rows_html = ""
    for r_i, r in enumerate(rows):
        cells = "".join([f"<td class='p-2'><input name='e{c_i}' value='{r[c_i] if c_i < len(r) else ''}' class='w-full bg-slate-900/70 border border-slate-700/70 rounded px-2 py-1 text-sm text-slate-100'></td>" for c_i in range(len(cols))])
        rows_html += f"<tr class='border-b border-slate-800 hover:bg-slate-800/40'><form method='POST'><input type='hidden' name='idx' value='{r_i}'>{cells}<td class='p-2 flex gap-1'><button name='action' value='edit' class='bg-emerald-600 hover:bg-emerald-500 px-2.5 py-1 rounded text-xs'>💾</button><button name='action' value='del' class='bg-rose-600 hover:bg-rose-500 px-2.5 py-1 rounded text-xs'>🗑</button></td></form></tr>"
    html = f"""<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>{board.get('title','لوحة التحكم')}</title>
    <script src='{_TW_CDN}'></script>
    <script src='{_CH_CDN}'></script>
    <link href='{_GF_CDN}' rel='stylesheet'>
    <style>
      body{{font-family:'Cairo',sans-serif;background:#0b1120;color:#f8fafc;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}}
      input, textarea{{-webkit-user-select:text;-moz-user-select:text;-ms-user-select:text;user-select:text;}}
    </style></head>
    <body oncontextmenu='return false;' class='p-4 md:p-8 max-w-7xl mx-auto'>
      <div class='flex flex-wrap justify-between items-center gap-4 mb-6 bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl'>
        <div>
          <span class='text-xs font-semibold px-2.5 py-1 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20'>لوحة بيانات تفاعلية</span>
          <h1 class='text-2xl font-bold mt-2 text-white'>📊 {board.get('title','لوحة القيادة الحية')}</h1>
        </div>
        <a href='/board/{bid}/export' class='bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-2.5 rounded-xl text-sm shadow transition'>📥 تصدير Excel</a>
      </div>
      <div class='grid grid-cols-1 md:grid-cols-3 gap-4 mb-6'>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>إجمالي السجلات</p><p class='text-3xl font-bold text-sky-400 mt-1'>{len(rows)}</p></div>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>متوسط المؤشر الرقمي</p><p class='text-3xl font-bold text-emerald-400 mt-1'>{avg_val}</p></div>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>أعلى قيمة مسجلة</p><p class='text-3xl font-bold text-amber-400 mt-1'>{max_val}</p></div>
      </div>
      <div class='bg-gradient-to-l from-slate-900 to-indigo-950/40 border border-indigo-500/30 p-5 rounded-2xl mb-6 shadow-lg'>
        <form method='POST' class='flex flex-col md:flex-row gap-3'>
          <input name='q' placeholder='اكتب التعديل المطلوب على الجدول (مثال: أضف 5 موظفين جدد لقسم التقنية أو عدّل إنجاز أحمد إلى 98%)...' class='flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500' required>
          <button name='action' value='chat' class='bg-sky-600 hover:bg-sky-500 text-white font-bold px-6 py-3 rounded-xl text-sm transition'>⚡ تطبيق التعديل</button>
        </form>
        {f"<div class='mt-3 p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-sm text-sky-300'>{ai_reply}</div>" if ai_reply else ""}
      </div>

      <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl mb-6'>
        <h3 class='text-sm font-bold text-slate-300 mb-3'>📈 التحليل البصري الفوري</h3>
        <div class='h-64'><canvas id='kpiChart'></canvas></div>
      </div>

      <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl mb-6'>
        <h3 class='text-sm font-bold text-slate-300 mb-3'>➕ إضافة سجل يدوي</h3>
        <form method='POST' class='flex flex-wrap items-end gap-3'>{add_inputs}<button name='action' value='add' class='bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-5 py-2 rounded-lg text-sm'>حفظ</button></form>
      </div>

      <div class='bg-slate-900 border border-slate-800 rounded-2xl overflow-x-auto'>
        <table class='w-full text-right border-collapse'>
          <thead><tr class='bg-slate-950 text-slate-300 text-xs uppercase'>{''.join([f'<th class="p-3 border-b border-slate-800">{c}</th>' for c in cols])}<th class='p-3 border-b border-slate-800'>تحكم</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>

      <script>
        document.addEventListener('keydown', function(e) {{
          if (e.ctrlKey && (e.key === 'c' || e.key === 'u' || e.key === 's' || e.key === 'p')) {{ e.preventDefault(); }}
        }});
        new Chart(document.getElementById('kpiChart'), {{
          type: 'bar',
          data: {{
            labels: {json.dumps(labels, ensure_ascii=False)},
            datasets: [{{ label: 'القيمة / المؤشر', data: {json.dumps(values)}, backgroundColor: 'rgba(56, 189, 248, 0.75)', borderColor: '#38bdf8', borderWidth: 1, borderRadius: 6 }}]
          }},
          options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }}, scales: {{ x: {{ ticks: {{ color: '#94a3b8' }} }}, y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }} }} }}
        }});
      </script>
    </body></html>"""
    return html

@app.route("/board/<int:bid>/export")
def export_board(bid):
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{bid}")
    if not res:
        return "Not Found", 404
    record = res if isinstance(res, list) else res
    board = json.loads(record["lesson_learned"])
    wb = Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(board.get("cols", []))
    for r in board.get("rows", []): ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"Dashboard_{bid}.xlsx")

@app.route("/site/<int:sid>", methods=["GET", "POST"])
def live_site(sid):
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{sid}")
    if not res:
        return "<h2 dir='rtl'>⚠️ الصفحة غير موجودة</h2>", 404
    record = res if isinstance(res, list) else res
    html_code = record.get("lesson_learned", "")
    if request.method == "POST":
        edit_req = request.form.get("edit_req", "").strip()
        if edit_req:
            updated = ai_ask(
                f"الكود الحالي للصفحة:\n{html_code}\n\nالتعديل المطلوب:\n{edit_req}",
                "أنت مطور واجهات ويب محترف. عدل كود HTML/CSS/JS التالي بناء على طلب المستخدم وأرجع الكود الكامل الصالح للعرض مباشرة بدون أي مقدمات أو علامات markdown.",
                mode="fast",
                use_cache=False
            )
            clean_html = updated.replace("```html", "").replace("```", "").strip()
            if "<html" in clean_html.lower() or "<body" in clean_html.lower() or "<div" in clean_html.lower():
                html_code = clean_html
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
    "📌 *الخدمات والقدرات المتاحة:*\n\n"
    "1️⃣ *تقارير وبحوث Word احترافية:* اكتب (تقرير وورد عن... أو بحث علمي عن...)\n"
    "2️⃣ *لوحات قيادة Excel + رسوم بيانية:* اكتب (لوحة إكسل لـ...)\n"
    "3️⃣ *عروض تقديمية PowerPoint بالصور:* اكتب (عرض بوربوينت عن...)\n"
    "4️⃣ *لوحات Power BI حية للتعديل المباشر:* اكتب (لوحة باور بي اي حية لـ...)\n"
    "5️⃣ *حزمة هندسة Power BI + DAX:* اكتب (دليل باور بي اي لـ...)\n"
    "6️⃣ *تصميم مواقع حية ورفعها على GitHub:* اكتب (صمم موقع لـ... أو ارفع على قيت هب...)\n"
    "7️⃣ *بصمة صوتية:* اكتب (اقرأ بصوت: النص المطلوب)\n"
    "8️⃣ *تقرير قياس الأداء والتطور:* اكتب (تقرير الأداء)\n\n"
    "✨ *التخصيص والتعديل الفوري:*\n"
    "• لحفظ قاعدة دائمة لأسلوبك: ابدأ رسالتك بـ *(قاعدة: ...)* أو *(ملاحظة: ...)*\n"
    "• لتعديل آخر مخرج وإعادة إنتاجه فوراً: اكتب *(تعديل: ملاحظتك هنا)*"
)


def _is_authorized(cid: str, sender: str) -> bool:
    if ALLOWED_GROUP and (cid == ALLOWED_GROUP or ALLOWED_GROUP in cid):
        return True

    cid_digits = "".join(filter(str.isdigit, cid.split("@"))) if cid else ""
    sender_digits = "".join(filter(str.isdigit, sender.split("@"))) if sender else ""

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

    if any(k in clean for k in ("القائمة", "المساعدة", "الخدمات", "/help", "قدراتك", "ايش تقدر تسوي", "وش تقدر تسوي")):
        send_msg(cid, HELP_MENU)
        return

    if clean in ("تقرير الأداء", "قياس الأداء", "kpi"):
        safe_run(make_kpi, cid)
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
    if len(sub_tasks) == 1 and (" و" in clean) and sum(w in clean for w in ("وورد", "اكسل", "إكسل", "بوربوينت", "باور بي", "موقع")) >= 2:
        topic = clean.split("عن ", 1)[-1] if "عن " in clean else clean
        sub_tasks = []
        if "وورد" in clean: sub_tasks.append(f"تقرير وورد عن {topic}")
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
        elif any(k in low for k in ("تقرير وورد", "ملف وورد", "word", "بحث علمي", "بحث أكاديمي", "بحث اكاديمي", "دراسة علمية")) and not any(k in low for k in ("باور بي", "power bi")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_word, cid, task)
        elif any(k in low for k in ("لوحة اكسل", "لوحة إكسل", "ملف اكسل", "ملف إكسل", "excel")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_excel, cid, task)
        elif any(k in low for k in ("بوربوينت", "عرض تقديمي", "شرائح", "pptx", "powerpoint")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_pptx, cid, task)
        elif any(k in low for k in ("صمم موقع", "انشئ موقع", "أنشئ موقع", "موقع الكتروني", "موقع إلكتروني", "صفحة هبوط", "موقع ويب")):
            EXECUTOR.submit(safe_run, _build_live_site, cid, task)
        elif any(k in low for k in ("ارفع على قيت", "ارفع على جيت", "github", "قيت هب", "مستودع")):
            EXECUTOR.submit(safe_run, _push_to_github, cid, task)
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

    saved = sb("POST", "self_learning_logs", {"user_role": "live_site", "lesson_learned": clean_html, "is_active": True})
    sid = saved[0].get("id", 1) if isinstance(saved, list) and saved else 1
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    site_link = f"{base_url}/site/{sid}" if base_url else f"/site/{sid}"
    send_msg(cid, f"🌐 *تم تصميم وإطلاق الموقع بنجاح!*\n\n🔗 *رابط الموقع المباشر (مع أداة التعديل الفوري أسفل الصفحة):*\n{site_link}\n\n💡 يمكنك أيضاً كتابة `تعديل: [وصف التعديل]` هنا في المحادثة لإعادة بنائه.")


def _push_to_github(cid: str, task: str):
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not gh_token:
        send_msg(cid, "⚠️ للرفع التلقائي على GitHub، أضف متغير `GITHUB_TOKEN` في إعدادات Render أولاً، أو اطلب الكود وسأجهزه لك مباشرة.")
        return
    send_msg(cid, "📦 جاري تجهيز الملفات البرمجية ورفعها إلى حسابك في GitHub...")
    repo_name = f"project-{int(os.times()[4])}"
    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    r_repo = requests.post("https://github.com", headers=headers, json={"name": repo_name, "private": False, "auto_init": True}, timeout=15)
    if r_repo.status_code not in (200, 201):
        send_msg(cid, f"⚠️ تعذر إنشاء المستودع في GitHub ({r_repo.status_code}).")
        return
    repo_info = r_repo.json()
    full_name = repo_info.get("full_name", "")
    html_url = repo_info.get("html_url", "")
    code_content = ai_ask(task, "اكتب الكود البرمجي الكامل والاحترافي لهذا المشروع بدون مقدمات أو شرح:", mode="general", use_cache=False)
    import base64
    b64_code = base64.b64encode(code_content.encode("utf-8")).decode("utf-8")
    requests.put(f"https://github.com{full_name}/contents/index.html", headers=headers, json={"message": "Initial commit", "content": b64_code}, timeout=15)
    send_msg(cid, f"✅ *تم إنشاء المستودع ورفع المشروع على GitHub بنجاح:*\n{html_url}")


def _handle_media_message(cid: str, mdata: dict, sname: str):
    file_data = mdata.get("fileMessageData", {})
    dl_url = file_data.get("downloadUrl", "")
    mime = file_data.get("mimeType", "")
    caption = file_data.get("caption", "").strip()
    if not dl_url:
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
        send_msg(cid, analysis)


@app.route("/whatsapp-webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    wtype = data.get("typeWebhook", "")
    if wtype not in ("incomingMessageReceived", "outgoingMessageReceived", "outgoingAPIMessageReceived"):
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

    bot_prefixes = ("🔍", "⚙️", "🛡️", "📑", "🌐", "🚀", "💻", "⚠", "✅", "🤖", "📊", "📄", "📽️", "👥", "💡", "🧠", "🎙", "📚", "🔄", "📌", "📦")
    if txt and cid and not any(txt.startswith(p) for p in bot_prefixes):
        print(f"IN: {wtype} | CID: {cid} | MSG: {txt[:25]}", flush=True)
        EXECUTOR.submit(_dispatch_smart, cid, txt, sname)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

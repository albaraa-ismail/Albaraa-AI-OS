import os, json, io
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from openpyxl import Workbook
from core_ai import sb, ai_ask_json, send_msg
from agent_brain import run_task
from safe_guard import safe_run
from office_tools import make_word, make_excel, make_pptx, make_powerbi_kit, make_kpi

app = Flask(__name__)
EXECUTOR = ThreadPoolExecutor(max_workers=6)
SEEN = set()
LAST_TASK = {}

_TW_CDN = "".join(["https:/", "/cdn.tailwindcss.", "com"])
_CH_CDN = "".join(["https:/", "/cdn.jsdelivr.", "net/npm/chart.js"])
_GF_CDN = "".join(["https:/", "/fonts.googleapis.", "com/css2?family=Cairo:wght@400;600;700&display=swap"])

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

    board = json.loads(res[0]["lesson_learned"])
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
                    f"أمر المستخدم: {q}\n\n"
                    "نفذ أمر المستخدم بدقة على الجدول (إضافة صفوف جديدة، تعديل قيم، حذف صفوف، أو إعادة بناء البيانات بالكامل).\n"
                    "أرجع JSON بهذا الهيكل الدقيق:\n"
                    '{"reply": "رسالة تأكيد قصيرة للمستخدم", "title": "عنوان اللوحة", "cols": [...], "rows": [[...], [...]]}'
                )
                ai_data = ai_ask_json(prompt, "أنت وكيل تحليل بيانات وPower BI محترف تقوم بتحديث الجداول بدقة.")
                if ai_data and isinstance(ai_data.get("rows"), list) and len(ai_data["rows"]) > 0:
                    board["title"] = ai_data.get("title", board.get("title", "لوحة التحكم"))
                    cols = ai_data.get("cols", cols)
                    rows = ai_data["rows"]
                    ai_reply = f"🤖 {ai_data.get('reply', 'تم تحديث البيانات بواسطة الوكيل بنجاح!')}"
                else:
                    ai_reply = "⚠️ تعذر على الوكيل معالجة التعديل حالياً، تأكد من مفاتيح الـ API في Render."

        board["cols"], board["rows"] = cols, rows
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(board, ensure_ascii=False)}, q=f"?id=eq.{bid}")

    labels = [str(r[0]) for r in rows[:12] if r]
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
    <style>body{{font-family:'Cairo',sans-serif;background:#0b1120;color:#f8fafc}}</style></head>
    <body class='p-4 md:p-8 max-w-7xl mx-auto'>
      <div class='flex flex-wrap justify-between items-center gap-4 mb-6 bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-xl'>
        <div>
          <span class='text-xs font-semibold px-2.5 py-1 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20'>Power BI Live Mode</span>
          <h1 class='text-2xl font-bold mt-2 text-white'>📊 {board.get('title','لوحة القيادة الحية')}</h1>
        </div>
        <a href='/board/{bid}/export' class='bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-4 py-2.5 rounded-xl text-sm shadow transition'>📥 تصدير Excel احترافي</a>
      </div>
      <div class='grid grid-cols-1 md:grid-cols-3 gap-4 mb-6'>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>إجمالي السجلات</p><p class='text-3xl font-bold text-sky-400 mt-1'>{len(rows)}</p></div>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>متوسط المؤشر الرقمي</p><p class='text-3xl font-bold text-emerald-400 mt-1'>{avg_val}</p></div>
        <div class='bg-slate-900 border border-slate-800 p-5 rounded-2xl'><p class='text-slate-400 text-xs'>أعلى قيمة مسجلة</p><p class='text-3xl font-bold text-amber-400 mt-1'>{max_val}</p></div>
      </div>

      <div class='bg-gradient-to-l from-slate-900 to-indigo-950/40 border border-indigo-500/30 p-5 rounded-2xl mb-6 shadow-lg'>
        <form method='POST' class='flex flex-col md:flex-row gap-3'>
          <input name='q' placeholder='أعطِ الوكيل أمراً مباشراً (مثال: أضف 5 موظفين جدد لقسم التقنية أو عدّل إنجاز أحمد إلى 98%)...' class='flex-1 bg-slate-950/80 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-sky-500' required>
          <button name='action' value='chat' class='bg-sky-600 hover:bg-sky-500 text-white font-bold px-6 py-3 rounded-xl text-sm transition'>⚡ تنفيذ أمر الوكيل</button>
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
    board = json.loads(res["lesson_learned"])
    wb = Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(board.get("cols", []))
    for r in board.get("rows", []): ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"PowerBI_Board_{bid}.xlsx")

@app.route("/", methods=["GET"])
def home():
    return "Albaraa AI OS Active", 200
HELP_MENU = (
    "🤖 *منظومة Albaraa AI OS التنفيذية*\n\n"
    "📌 *القدرات والأدوات المتاحة حالياً:*\n"
    "1️⃣ *تقارير Word احترافية:* اكتب (تقرير وورد عن...)\n"
    "2️⃣ *لوحات قيادة Excel + رسوم بيانية:* اكتب (لوحة إكسل لـ...)\n"
    "3️⃣ *عروض تقديمية PowerPoint:* اكتب (عرض بوربوينت عن...)\n"
    "4️⃣ *لوحات Power BI حية + DAX:* اكتب (لوحة باور بي اي حية لـ...)\n"
    "5️⃣ *حزمة هندسة Power BI:* اكتب (دليل باور بي اي لـ...)\n"
    "6️⃣ *تنفيذ عدة مهام معاً:* اكتب طلباتك في سطور متعددة أو في جملة واحدة\n"
    "7️⃣ *البحث والاستقصاء والبرمجة:* اكتب (ابحث عن... أو برمج لي...)\n"
    "8️⃣ *تقرير قياس أداء النظام:* اكتب (تقرير الأداء)\n\n"
    "🧠 *نظام التغذية الراجعة والتعلم الذاتي:*\n"
    "• لحفظ قاعدة دائمة للمستقبل: ابدأ رسالتك بـ *(قاعدة: ...)* أو *(ملاحظة: ...)*\n"
    "• لتعديل آخر مخرج وإعادة إنتاجه فوراً: اكتب *(تعديل: ملاحظتك هنا)*"
)

def _run_with_tip(fn, cid, task):
    fn(cid, task)
    send_msg(cid, "💡 *لتعديل هذا المخرج وإعادة إنتاجه فوراً وفق ملاحظتك، أرسل:*\n`تعديل: [اكتب التعديل المطلوب هنا]`")

def _dispatch_smart(cid: str, txt: str, sname: str):
    clean = txt.strip()
    if clean in ("القائمة", "المساعدة", "الخدمات", "/help", "قدراتك", "ايش تقدر تسوي", "وش تقدر تسوي"):
        send_msg(cid, HELP_MENU)
        return

    if clean in ("تقرير الأداء", "قياس الأداء", "kpi"):
        safe_run(make_kpi, cid)
        return

    # تفعيل التغذية الراجعة والتصحيح الفوري
    for prefix in ("تعديل:", "ملاحظة:", "قاعدة:", "تغذية راجعة:"):
        if clean.startswith(prefix):
            note = clean[len(prefix):].strip()
            if not note:
                send_msg(cid, "⚠️ اكتب ملاحظتك بعد الكلمة المفتاحية، مثال:\n`تعديل: اجعل التقرير مختصراً مع إضافة أمثلة واقعية`")
                return
            sb("POST", "self_learning_logs", {"user_role": "admin", "lesson_learned": note, "is_active": True})
            prev_task = LAST_TASK.get(cid, "")
            if prefix == "تعديل:" and prev_task:
                send_msg(cid, f"🧠 *تم حفظ الملاحظة في الذاكرة الدائمة!*\n🔄 جاري إعادة تنفيذ طلبك السابق وتطبيق التعديل فوراً:\n_{prev_task}_")
                refined_task = f"{prev_task}\n[تعديل وملاحظة إلزامية من المستخدم يجب تطبيقها بدقة]: {note}"
                _dispatch_smart(cid, refined_task, sname)
            else:
                send_msg(cid, f"✅ *تم حفظ القاعدة في الذاكرة الدائمة (Supabase):*\n«{note}»\n\nسيتم الالتزام بها في جميع الطلبات القادمة. *(ولإعادة توليد آخر مخرج بتعديل فوري ابدأ رسالتك بـ `تعديل:`)*")
            return

    LAST_TASK[cid] = clean

    # تقسيم الطلبات المتعددة في رسالة واحدة
    sub_tasks = [t.strip() for t in clean.splitlines() if len(t.strip()) > 3 and not t.strip().startswith("[تعديل")]
    if len(sub_tasks) == 1 and (" و" in clean) and sum(w in clean for w in ("وورد", "اكسل", "إكسل", "بوربوينت", "باور بي")) >= 2:
        topic = clean.split("عن ", 1)[-1] if "عن " in clean else clean
        sub_tasks = []
        if "وورد" in clean: sub_tasks.append(f"تقرير وورد عن {topic}")
        if any(k in clean for k in ("اكسل", "إكسل")): sub_tasks.append(f"لوحة إكسل عن {topic}")
        if "بوربوينت" in clean: sub_tasks.append(f"عرض بوربوينت عن {topic}")
        if "باور بي" in clean: sub_tasks.append(f"دليل باور بي اي عن {topic}")

    for task in (sub_tasks or [clean])[:4]:
        low = task.lower()
        if any(k in low for k in ("تقرير وورد", "ملف وورد", "word")) and not any(k in low for k in ("باور بي", "power bi", "حية")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_word, cid, task)
        elif any(k in low for k in ("لوحة اكسل", "لوحة إكسل", "ملف اكسل", "ملف إكسل", "excel")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_excel, cid, task)
        elif any(k in low for k in ("بوربوينت", "عرض تقديمي", "شرائح", "pptx", "powerpoint")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_pptx, cid, task)
        elif any(k in low for k in ("دليل باور بي", "هندسة باور بي", "dax")):
            EXECUTOR.submit(safe_run, _run_with_tip, make_powerbi_kit, cid, task)
        else:
            EXECUTOR.submit(safe_run, run_task, cid, task, "admin", sname)

@app.route("/whatsapp-webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("typeWebhook") != "incomingMessageReceived":
        return jsonify({"status": "ignored"}), 200
    mid = data.get("idMessage", "")
    if _mark_seen(mid):
        return jsonify({"status": "dup"}), 200
    mdata = data.get("messageData", {})
    txt = (mdata.get("textMessageData", {}).get("textMessage") or mdata.get("extendedTextMessageData", {}).get("text") or "").strip()
    cid = data.get("senderData", {}).get("chatId", "")
    sname = data.get("senderData", {}).get("senderName", "User")
    if txt and cid and not any(txt.startswith(p) for p in ("🔍", "⚙️", "🛡️", "📑", "🌐", "🚀", "💻", "⚠", "✅", "🤖", "📊", "📄", "📽️", "👥", "💡", "🧠")):
        print(f"IN: incomingMessageReceived | CID: {cid} | MSG: {txt[:25]}", flush=True)
        EXECUTOR.submit(_dispatch_smart, cid, txt, sname)
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

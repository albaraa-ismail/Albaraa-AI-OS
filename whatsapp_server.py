import os
import json
import threading
import io
from flask import Flask, request, jsonify, send_file
from openpyxl import Workbook
from core_ai import sb, ai_ask_json
from agent_brain import run_task
from safe_guard import safe_run

app = Flask(__name__)
SEEN = set()

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
    <script src='https://tailwindcss.com'></script>
    <script src='https://jsdelivr.net'></script>
    <link href='https://googleapis.com' rel='stylesheet'>
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
    board = json.loads(res[0]["lesson_learned"])
    wb = Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(board.get("cols", []))
    for r in board.get("rows", []): ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"PowerBI_Board_{bid}.xlsx")

@app.route("/", methods=["GET"])
def home():
    return "Albaraa AI OS Active", 200

@app.route("/whatsapp-webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    mid = data.get("idMessage", "")
    if mid in SEEN: return jsonify({"status": "dup"}), 200
    SEEN.add(mid)
    mdata = data.get("messageData", {})
    txt = (mdata.get("textMessageData", {}).get("textMessage") or mdata.get("extendedTextMessageData", {}).get("text") or "").strip()
    cid = data.get("senderData", {}).get("chatId", "")
    sname = data.get("senderData", {}).get("senderName", "User")

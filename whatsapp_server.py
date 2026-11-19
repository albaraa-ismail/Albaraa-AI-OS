import os
import json
import threading
import io
from flask import Flask, request, jsonify, send_file
from openpyxl import Workbook
from core_ai import sb, ai_ask
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
    cols = board.get("cols", ["البند", "الحالة"])
    rows = board.get("rows", [])
    ai_reply = ""
    if request.method == "POST":
        act = request.form.get("action")
        if act == "add":
            rows.append([request.form.get(f"c{i}", "").strip() for i in range(len(cols))])
        elif act == "edit":
            idx = int(request.form.get("idx", -1))
            if 0 <= idx < len(rows):
                rows[idx] = [request.form.get(f"e{i}", "").strip() for i in range(len(cols))]
        elif act == "del":
            idx = int(request.form.get("idx", -1))
            if 0 <= idx < len(rows):
                rows.pop(idx)
        elif act == "chat":
            q = request.form.get("q", "").strip()
            if q:
                p = f"الجدول الحالي: {json.dumps(board, ensure_ascii=False)}\nالطلب: {q}\nأجب باختصار. وإذا كان الطلب إضافة أو تعديل صفوف، أرجع JSON فقط فيه title و cols و rows."
                ans = ai_ask(p, "أنت مساعد لوحة تحكم ذكي.")
                if "{" in ans and "rows" in ans:
                    try:
                        new_b = json.loads(ans[ans.find("{"):ans.rfind("}")+1])
                        if isinstance(new_b.get("rows"), list) and len(new_b["rows"]) > 0:
                            board.update(new_b)
                            cols, rows = board.get("cols", cols), board.get("rows", rows)
                            ai_reply = "✅ تم تحديث الجدول وحفظه!"
                        else:
                            ai_reply = ans
                    except Exception:
                        ai_reply = ans
                else:
                    ai_reply = ans
        board["cols"], board["rows"] = cols, rows
        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(board, ensure_ascii=False)}, q=f"?id=eq.{bid}")
    chat_ui = f"<div class='card'><form method='POST'><input name='q' placeholder='اطلب من الوكيل تعديل الجدول أو تحليله...' required><button name='action' value='chat'>إرسال للوكيل</button></form><p style='color:#38bdf8'>{ai_reply}</p></div>"
    add_inputs = "".join([f"<div><label>{c}</label><input name='c{i}' required></div>" for i, c in enumerate(cols)])
    rows_html = ""
    for r_i, r in enumerate(rows):
        cells = "".join([f"<td><input name='e{c_i}' value='{r[c_i] if c_i < len(r) else ''}'></td>" for c_i in range(len(cols))])
        rows_html += f"<tr><form method='POST'><input type='hidden' name='idx' value='{r_i}'>{cells}<td><button name='action' value='edit'>💾</button><button name='action' value='del' style='background:#dc2626'>🗑</button></td></form></tr>"

    html = f"""<!DOCTYPE html><html dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>{board.get('title','لوحة التحكم')}</title><style>body{{background:#0f172a;color:#f8fafc;font-family:sans-serif;padding:15px}}
    .card{{background:#1e293b;padding:15px;border-radius:12px;margin-bottom:15px}}input,button{{padding:8px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#fff;margin:3px}}
    button{{background:#10b981;border:none;cursor:pointer}}table{{width:100%;border-collapse:collapse}}th,td{{padding:8px;border-bottom:1px solid #334155;text-align:right}}</style></head>
    <body><h2>📊 {board.get('title','لوحة التحكم الحية')}</h2><div class='card'>السجلات: {len(rows)} | <a href='/board/{bid}/export' style='color:#38bdf8'>📥 تحميل Excel</a></div>
    {chat_ui}<div class='card'><form method='POST'>{add_inputs}<button name='action' value='add'>➕ إضافة وحفظ</button></form></div>
    <div class='card' style='overflow-x:auto'><table><tr>{''.join([f'<th>{c}</th>' for c in cols])}<th>إجراء</th></tr>{rows_html}</table></div></body></html>"""
    return html

@app.route("/board/<int:bid>/export")
def export_board(bid):
    res = sb("GET", "self_learning_logs", q=f"?id=eq.{bid}")
    board = json.loads(res["lesson_learned"])
    wb = Workbook(); ws = wb.active
    ws.append(board.get("cols", []))
    for r in board.get("rows", []): ws.append(r)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f"board_{bid}.xlsx")

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
    if txt and cid and not any(txt.startswith(p) for p in ("🔍", "⚙️", "🛡️", "📑", "🌐", "🚀", "💻", "⚠", "✅")):
        print(f"IN: {data.get('typeWebhook')} | CID: {cid} | MSG: {txt[:20]}", flush=True)
        threading.Thread(target=safe_run, args=(run_task, cid, txt, "admin", sname), daemon=True).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

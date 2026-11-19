import os, json, threading
from flask import Flask, request, jsonify, send_file
from agent_brain import run_task
from safe_guard import safe_run
from auto_scheduler import start_scheduler
from media_reader import analyze_media
from core_ai import sb, ai_ask

app = Flask(__name__)
start_scheduler()
SEEN = set()
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966575475336").strip()
ALLOWED_GROUPS = [g.strip() for g in os.environ.get("ALLOWED_GROUP", "120363413772983962@g.us").split(",") if "@g.us" in g]

def _page(title, body):
    css = "body{background:#0b1120;color:#fff;font-family:Tahoma;padding:15px} .card{background:#1e293b;padding:16px;border-radius:14px;margin-bottom:14px;border:1px solid #334155} .grid{display:grid;grid-template-columns:1fr 1fr;gap:8px} input{width:92%;background:#0f172a;color:#fff;border:1px solid #475569;padding:8px;border-radius:8px;margin-top:3px} button{background:#10b981;color:#fff;border:none;padding:9px 14px;border-radius:8px;font-weight:bold;margin-top:8px} .del{background:#ef4444}"
    return f"<!DOCTYPE html><html dir='rtl'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{title}</title><style>{css}</style></head><body><h2>📊 {title}</h2>{body}</body></html>"
@app.route("/board/<int:bid>/export")
def export_board(bid):
    import openpyxl
    rows_db = sb("GET", "self_learning_logs", q=f"?id=eq.{bid}") or []
    row = next(iter(rows_db), None)
    if not row: return "غير موجود", 404
    board = json.loads(row.get("lesson_learned", "{}"))
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(board.get("cols", []))
    for r in board.get("rows", []): ws.append(r)
    path = f"/tmp/board_{bid}.xlsx"; wb.save(path)
    return send_file(path, as_attachment=True, download_name=f"Board_{bid}.xlsx")

@app.route("/board/<int:bid>", methods=["GET", "POST"])
def custom_board(bid):
    rows_db = sb("GET", "self_learning_logs", q=f"?id=eq.{bid}") or []
    row = next(iter(rows_db), None)
    if not row: return "اللوحة غير موجودة", 404
    board = json.loads(row.get("lesson_learned", "{}"))
    cols, rows = board.get("cols", []), board.get("rows", [])
    if request.method == "POST":
        act = request.form.get("action")
        if act == "add": rows.append([request.form.get(f"c{i}", "") for i in range(len(cols))])
        elif act == "save": rows[int(request.form.get("idx"))] = [request.form.get(f"c{i}", "") for i in range(len(cols))]
        elif act == "del": rows.pop(int(request.form.get("idx")))
        elif act == "chat":
            q = request.form.get("q", "").strip()
            if q:
                p = f"الجدول: {json.dumps(board, ensure_ascii=False)}\nالطلب: {q}\nإذا كان الطلب تعديل أو إضافة، أرجع JSON فقط فيه cols و rows و title. وإلا أجب باختصار."
                ans = ai_ask(p, "أنت مساعد لوحة تحكم ذكي.")
                if "{" in ans and "rows" in ans:
                    board.update(json.loads(ans[ans.find("{"):ans.rfind("}")+1]))
                    cols, rows = board.get("cols", cols), board.get("rows", rows)
                    ai_reply = "✅ تم تحديث الجدول وحفظه بنجاح!"
                else:
                    ai_reply = ans

        sb("PATCH", "self_learning_logs", {"lesson_learned": json.dumps(board, ensure_ascii=False)}, q=f"?id=eq.{bid}")
    bars = ""
    for r in rows[:10]:
        lbl = next(iter(r[1:2]), next(iter(r), ""))
        num = next((int(float(x)) for x in r if str(x).replace('.','',1).isdigit() and 1 <= float(x) <= 100), 75)
        bars += f"<div style='margin:6px 0'><small>{lbl} ({num}%)</small><div style='background:#0f172a;border-radius:6px;height:10px'><div style='background:#10b981;width:{num}%;height:10px;border-radius:6px'></div></div></div>"
    js = "<script>function f(q){document.querySelectorAll('.rec').forEach(c=>{c.style.display=c.innerHTML.includes(q)?'block':'none'})}</script>"
    top = f"<div class='grid'><div class='card'><b>📊 السجلات: {len(rows)}</b><br><a href='/board/{bid}/export' style='color:#38bdf8;font-weight:bold'>📥 تحميل Excel</a></div><div class='card'><b>📈 مؤشر الأداء الحي</b>{bars}</div></div>"
    srch = f"<input placeholder='🔍 ابحث بالاسم أو القسم أو الرقم...' onkeyup='f(this.value)' style='margin-bottom:12px;width:96%'>{js}"
    chat_ui = f"<div class='card'><form method='POST'><input name='q' placeholder='اطلب من الوكيل تعديل الجدول أو تحليله...' required><button name='action' value='chat'>إرسال للوكيل</button></form><p style='color:#38bdf8'>{locals().get('ai_reply','')}</p></div>"
    add_f = "".join([f"<div><small>{c}</small><input name='c{i}' required></div>" for i, c in enumerate(cols)])
    html = f"{top}{chat_ui}{srch}<div class='card'><h3>➕ إضافة سجل جديد</h3><form method='POST'><div class='grid'>{add_f}</div><button name='action' value='add'>إضافة وحفظ</button></form></div>"
    for idx, r in enumerate(rows):
        flds = "".join([f"<div><small>{cols[i] if i<len(cols) else ''}</small><input name='c{i}' value='{v}'></div>" for i, v in enumerate(r)])
        html += f"<div class='card rec'><h4>#{idx+1} — {next(iter(r), '')}</h4><form method='POST'><input type='hidden' name='idx' value='{idx}'><div class='grid'>{flds}</div><button name='action' value='save'>💾 حفظ التعديل</button> <button class='del' name='action' value='del'>🗑️ حذف</button></form></div>"
    return _page(board.get("title", "لوحة التحكم"), html)
def process_incoming(cid, msg, m_url, m_mime, role, sname):
    final_msg = analyze_media(m_url, m_mime, msg) if m_url else msg
    if final_msg: safe_run(run_task, cid, final_msg, role, sname)

@app.route("/", methods=["GET", "POST"])
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return jsonify({"status": "online"}), 200
    d = request.get_json(silent=True) or {}
    wt = d.get("typeWebhook", "")
    sd, md = d.get("senderData", {}), d.get("messageData", {})
    cid, sender, sname = sd.get("chatId", "").strip(), sd.get("sender", ""), sd.get("senderName", "User")
    f_data = md.get("fileMessageData") or md.get("audioMessageData") or md.get("imageMessageData") or md.get("documentMessageData") or {}
    msg = (md.get("textMessageData", {}).get("textMessage", "") or md.get("extendedTextMessageData", {}).get("text", "") or f_data.get("caption", "")).strip()
    m_url, m_mime = f_data.get("downloadUrl", ""), f_data.get("mimeType", "audio/ogg")
    print(f"IN: {wt} | CID: {cid} | URL: {bool(m_url)} | MSG: {msg[:15]}")
    if not cid or (not msg and not m_url) or msg.startswith(("🤖", "⏳", "🎬", "🧬", "📊", "📄", "📽️", "⚠️", "🔐", "✅", "🚀", "📈", "🛠️", "🔔", "⏰", "💾", "📋", "🗑️")): return jsonify({"status": "ignore"}), 200
    mid = d.get("idMessage", "")
    if mid and mid in SEEN: return jsonify({"status": "dup"}), 200
    if mid: SEEN.add(mid)
    is_out = "outgoing" in wt
    is_admin = is_out or (ADMIN_PHONE in (sender or cid))
    if not (("@c.us" in cid and ADMIN_PHONE in cid) or (cid in ALLOWED_GROUPS)):
        return jsonify({"status": "blocked"}), 200
    role = "admin" if is_admin else "co_lead"
    threading.Thread(target=process_incoming, args=(cid, msg, m_url, m_mime, role, sname)).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

import os, threading
from flask import Flask, request, jsonify
from agent_brain import run_task
from safe_guard import safe_run
from auto_scheduler import start_scheduler
from media_reader import analyze_media

app = Flask(__name__)
start_scheduler()
SEEN = set()
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966575475336").strip()
ALLOWED_GROUP = os.environ.get("ALLOWED_GROUP", "120363413772983962@g.us").strip()

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
    print(f"IN: {wt} | URL: {bool(m_url)} | MSG: {msg[:15]}")
    if not cid or (not msg and not m_url) or msg.startswith(("🤖", "⏳", "🧬", "📊", "📄", "📽️", "⚠️", "🔐", "✅", "🚀", "📈", "🛠️", "🔔", "⏰", "💾", "📋", "🗑️")): return jsonify({"status": "ignore"}), 200
    mid = d.get("idMessage", "")
    if mid and mid in SEEN: return jsonify({"status": "dup"}), 200
    if mid: SEEN.add(mid)
    is_out = "outgoing" in wt
    is_admin = is_out or (ADMIN_PHONE in (sender or cid))
    if not (("@c.us" in cid and ADMIN_PHONE in cid) or (cid == ALLOWED_GROUP)): return jsonify({"status": "blocked"}), 200
    role = "admin" if is_admin else "co_lead"
    threading.Thread(target=process_incoming, args=(cid, msg, m_url, m_mime, role, sname)).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

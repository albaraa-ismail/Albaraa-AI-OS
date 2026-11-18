import os, threading
from flask import Flask, request, jsonify
from agent_brain import run_task
from safe_guard import safe_run

app = Flask(__name__)
SEEN = set()
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966575475336").strip()
AHMED_PHONE = os.environ.get("AHMED_PHONE", "").strip()
ALLOWED_GROUP = os.environ.get("ALLOWED_GROUP", "").strip()

@app.route("/", methods=["GET", "POST"])
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return jsonify({"status": "online"}), 200
    d = request.get_json(silent=True) or {}
    wt = d.get("typeWebhook", "")
    sd, md = d.get("senderData", {}), d.get("messageData", {})
    cid, sender, sname = sd.get("chatId", ""), sd.get("sender", ""), sd.get("senderName", "User")
    msg = (md.get("textMessageData", {}).get("textMessage", "") or md.get("extendedTextMessageData", {}).get("text", "")).strip()
    print(f"HOOK: {wt} | CID: {cid} | MSG: {msg[:20]}")
    if not cid or not msg or msg.startswith(("🤖", "⏳", "🧬", "📊", "📄", "📽️", "⚠️")): return jsonify({"status": "ignore"}), 200
    mid = d.get("idMessage", "")
    if mid and mid in SEEN: return jsonify({"status": "dup"}), 200
    if mid: SEEN.add(mid)
    is_out = "outgoing" in wt
    who = sender or (ADMIN_PHONE if is_out else cid)
    is_admin = is_out or (ADMIN_PHONE in who)
    is_ahmed = bool(AHMED_PHONE and AHMED_PHONE in who)
    is_self = ("@c.us" in cid and ADMIN_PHONE in cid)
    is_grp = bool(ALLOWED_GROUP and cid == ALLOWED_GROUP and (is_admin or is_ahmed))
    if not (is_self or is_grp): return jsonify({"status": "blocked"}), 200
    role = "admin" if is_admin else "co_lead"
    threading.Thread(target=safe_run, args=(run_task, cid, msg, role, sname)).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

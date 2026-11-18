import os
import threading
import logging
from collections import OrderedDict
from flask import Flask, request, jsonify
from agent_brain import run_task
from safe_guard import safe_run
from media_vision import download_whatsapp_file, MEDIA_VAULT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WhatsAppWebhook")

app = Flask(__name__)

class BoundedCache:
    def __init__(self, max_size=2000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = threading.Lock()

    def is_duplicate(self, msg_id: str) -> bool:
        if not msg_id:
            return False
        with self.lock:
            if msg_id in self.cache:
                return True
            self.cache[msg_id] = True
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
            return False

SEEN_MESSAGES = BoundedCache(max_size=2000)
ADMIN_PHONE = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "966575475336")))
ALLOWED_GROUPS = {
    g.strip() for g in os.environ.get("ALLOWED_GROUP", "120363413772983962@g.us").split(",") if g.strip()
}
BOT_PREFIXES = ("🤖", "⏳", "🧬", "📊", "📄", "📽️", "💻", "⚠️", "✅", "❌", "📥", "👁️")

def parse_incoming_message(message_data: dict):
    """استخراج النص والوسائط والملفات (بما فيها الرسائل المُعاد توجيهها)"""
    if not message_data:
        return "", None

    type_msg = message_data.get("typeMessage", "")
    text = (
        message_data.get("textMessageData", {}).get("textMessage")
        or message_data.get("extendedTextMessageData", {}).get("text")
        or ""
    ).strip()

    media_info = None
    file_data = message_data.get("fileMessageData") or {}
    if file_data.get("downloadUrl"):
        dl_url = file_data.get("downloadUrl", "")
        fname = file_data.get("fileName") or f"media_{type_msg}"
        mime = file_data.get("mimeType", "application/octet-stream")
        caption = (file_data.get("caption") or "").strip()
        if caption:
            text = caption
        media_info = {"url": dl_url, "filename": fname, "mime": mime, "type": type_msg}

    return text, media_info
@app.route("/", methods=["GET", "POST"])
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "online", "service": "Albaraa AI OS"}), 200

    payload = request.get_json(silent=True) or {}
    webhook_type = payload.get("typeWebhook", "")

    if webhook_type not in ("incomingMessageReceived", "outgoingMessageReceived"):
        return jsonify({"status": "ignored_type"}), 200

    msg_id = payload.get("idMessage", "")
    if SEEN_MESSAGES.is_duplicate(msg_id):
        return jsonify({"status": "duplicate"}), 200

    sender_data = payload.get("senderData", {})
    message_data = payload.get("messageData", {})
    instance_data = payload.get("instanceData", {})

    chat_id = sender_data.get("chatId", "").strip()
    sender = sender_data.get("sender", "").strip()
    sender_name = sender_data.get("senderName", "User").strip() or "User"
    bot_wid = instance_data.get("wid", "").strip()

    msg_text, media_info = parse_incoming_message(message_data)

    if not chat_id or (not msg_text and not media_info) or msg_text.startswith(BOT_PREFIXES):
        return jsonify({"status": "ignored_content"}), 200

    is_outgoing = (webhook_type == "outgoingMessageReceived")
    is_group = chat_id.endswith("@g.us")

    is_self_chat = False
    if not is_group:
        if is_outgoing and (ADMIN_PHONE in chat_id or chat_id == bot_wid or chat_id.endswith("@lid")):
            is_self_chat = True
        elif not is_outgoing and (ADMIN_PHONE in sender or ADMIN_PHONE in chat_id):
            is_self_chat = True

    is_allowed_group = is_group and (chat_id in ALLOWED_GROUPS)
    if not (is_self_chat or is_allowed_group):
        return jsonify({"status": "blocked"}), 200

    role = "admin" if (is_outgoing or ADMIN_PHONE in sender or ADMIN_PHONE in chat_id) else "co_lead"

    def process_pipeline():
        if media_info:
            logger.info(f"Downloading media: {media_info['filename']} ({media_info['type']})")
            local_path = download_whatsapp_file(media_info["url"], media_info["filename"])
            if local_path:
                MEDIA_VAULT[chat_id] = {
                    "path": local_path,
                    "filename": media_info["filename"],
                    "mime": media_info["mime"],
                    "type": media_info["type"]
                }
        safe_run(run_task, chat_id, msg_text, role, sender_name)

    threading.Thread(target=process_pipeline, daemon=True).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

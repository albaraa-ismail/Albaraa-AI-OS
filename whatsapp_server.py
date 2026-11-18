import os
import threading
import logging
from collections import OrderedDict
from flask import Flask, request, jsonify
from agent_brain import run_task
from safe_guard import safe_run

# إعداد نظام سجلات (Logs) احترافي وواضح في Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("WhatsAppWebhook")

app = Flask(__name__)

# ذاكرة مؤقتة ذكية للرسائل المعالجة (تحتفظ بآخر 2000 رسالة فقط لمنع استهلاك الرام)
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

# تحميل الإعدادات وتنظيفها من أي مسافات أو رموز زائدة
ADMIN_PHONE = "".join(filter(str.isdigit, os.environ.get("ADMIN_PHONE", "966575475336")))
ALLOWED_GROUPS = {
    g.strip() for g in os.environ.get("ALLOWED_GROUP", "120363413772983962@g.us").split(",") if g.strip()
}

# الإيموجيات الخاصة بردود الوكيل لمنع دخوله في حلقة ردود لا نهائية
BOT_PREFIXES = ("🤖", "⏳", "🧬", "📊", "📄", "📽️", "⚠️", "✅", "❌")

def extract_text(message_data: dict) -> str:
    """استخراج النص من مختلف أنواع رسائل واتساب (عادية، رد على رسالة، أو مع رابط)"""
    if not message_data:
        return ""
    msg = (
        message_data.get("textMessageData", {}).get("textMessage")
        or message_data.get("extendedTextMessageData", {}).get("text")
        or message_data.get("quotedMessage", {}).get("textMessage")
        or ""
    )
    return msg.strip()

@app.route("/", methods=["GET", "POST"])
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return jsonify({"status": "online", "service": "Albaraa AI OS"}), 200

    payload = request.get_json(silent=True) or {}
    webhook_type = payload.get("typeWebhook", "")

    # 1. قبول الرسائل الواردة، والرسائل الصادرة من جوالك يدوياً فقط (تجاهل outgoingAPIMessageReceived)
    if webhook_type not in ("incomingMessageReceived", "outgoingMessageReceived"):
        return jsonify({"status": "ignored_type", "type": webhook_type}), 200

    # 2. منع التكرار
    msg_id = payload.get("idMessage", "")
    if SEEN_MESSAGES.is_duplicate(msg_id):
        return jsonify({"status": "duplicate"}), 200

    sender_data = payload.get("senderData", {})
    message_data = payload.get("messageData", {})
    instance_data = payload.get("instanceData", {})

    chat_id = sender_data.get("chatId", "").strip()
    sender = sender_data.get("sender", "").strip()
    sender_name = sender_data.get("senderName", "User").strip() or "User"
    bot_wid = instance_data.get("wid", "").strip() # المعرّف الفعلي لحساب الوكيل

    msg_text = extract_text(message_data)

    # 3. تجاهل الرسائل الفارغة أو التي تبدأ ببصمة الوكيل
    if not chat_id or not msg_text or msg_text.startswith(BOT_PREFIXES):
        return jsonify({"status": "ignored_content"}), 200

    is_outgoing = (webhook_type == "outgoingMessageReceived")
    is_group = chat_id.endswith("@g.us")

    # 4. التحقق الذكي من المحادثة الخاصة (يدعم صيغة @c.us وصيغة @lid الجديدة)
    is_self_chat = False
    if not is_group:
        # إذا كنت تراسل نفسك (صادرة إلى رقمك أو معرّف البوت أو بصيغة @lid خاصة بك)
        if is_outgoing and (ADMIN_PHONE in chat_id or chat_id == bot_wid or chat_id.endswith("@lid")):
            is_self_chat = True
        # إذا أرسلت للوكيل من رقمك الخاص إلى رقم وكيل مستقل
        elif not is_outgoing and (ADMIN_PHONE in sender or ADMIN_PHONE in chat_id):
            is_self_chat = True

    is_allowed_group = is_group and (chat_id in ALLOWED_GROUPS)

    # 5. رفض أي محادثة غير مصرح بها مع تسجيل السبب في Logs
    if not (is_self_chat or is_allowed_group):
        logger.info(f"Blocked message | type={webhook_type} | chatId={chat_id} | sender={sender}")
        return jsonify({"status": "blocked"}), 200

    # 6. تحديد الصلاحية (Admin لك، و co_lead لبقية أعضاء القروب)
    is_admin = is_outgoing or (ADMIN_PHONE in sender) or (ADMIN_PHONE in chat_id)
    role = "admin" if is_admin else "co_lead"

    logger.info(f"Accepted | role={role} | chat={chat_id} | user={sender_name} | msg={msg_text[:40]}")

    # 7. تنفيذ المهمة في الخلفية بأمان
    threading.Thread(
        target=safe_run,
        args=(run_task, chat_id, msg_text, role, sender_name),
        daemon=True
    ).start()

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

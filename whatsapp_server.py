import os, requests
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)
ai_os = MultiAgentSystem()

GREEN_API_ID = os.environ.get("GREEN_API_ID", "").strip()
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "").strip()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online"}), 200

@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    data = request.get_json(silent=True) or {}
    wid = data.get('instanceData', {}).get('wid', '')
    chat_id = data.get('senderData', {}).get('chatId') or data.get('chatId', '')
    msg_data = data.get('messageData', {})
    user_msg = (msg_data.get('textMessageData', {}).get('textMessage') or 
                msg_data.get('extendedTextMessageData', {}).get('text') or "").strip()

    if wid and chat_id == wid and user_msg and not user_msg.startswith("*تقرير"):
        constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
        try:
            ai_os.chief.orchestrate_task(user_msg, constraints)
            refined = ai_os.research.refine_query(user_msg, constraints)
            build_log = ai_os.builder.generate_code_structure("AI Framework")
            eval_log = ai_os.trainer.evaluate_performance("Execution OK")
            
            reply = (
                f"*تقرير Albaraa-AI-OS*\n"
                f"--------------------\n"
                f"*القائد:* تم استلام الطلب.\n"
                f"*البحث:* {refined}\n"
                f"*البناء:* {build_log}\n"
                f"*التقييم:* الدقة {eval_log['accuracy']}\n"
                f"--------------------"
            )
            host = "7107" + ".api." + "greenapi.com"
            url = f"https://{host}/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
            res = requests.post(url, json={"chatId": chat_id, "message": reply}, timeout=15)
            print("الإرسال:", res.status_code, res.text, flush=True)
        except Exception as e:
            print("خطأ:", e, flush=True)
            
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

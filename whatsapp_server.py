import os
import requests
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)

GREEN_API_ID = os.environ.get("GREEN_API_ID", "").strip()
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "").strip()

ai_os = MultiAgentSystem()

def send_whatsapp_response(chat_id, text_to_send):
    host = "7107" + ".api." + "greenapi.com"
    url = f"https://{host}/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": chat_id, "message": text_to_send}
    headers = {'Content-Type': 'application/json'}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        print("نتيجة الإرسال:", res.status_code, res.text, flush=True)
        return res.status_code == 200
    except Exception as e:
        print("خطأ:", str(e), flush=True)
        return False

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "system": "Albaraa-AI-OS"}), 200

@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    data = request.get_json(silent=True) or {}
    wid = data.get('instanceData', {}).get('wid', '')
    body = data.get('body', {})
    chat_id = body.get('senderData', {}).get('chatId', '')
    msg_data = body.get('messageData', {})
    user_msg = msg_data.get('textMessageData', {}).get('textMessage', '').strip()

    if wid and chat_id == wid and user_msg and not user_msg.startswith("*تقرير Albaraa-AI-OS*"):
        constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
        try:
            init_status = ai_os.chief.orchestrate_task(user_msg, constraints)
            refined_query = ai_os.research.refine_query(user_msg, constraints)
            
            mock_data = [
                {"name": "GitHub Copilot", "type": "Paid"},
                {"name": "VS Code Core", "type": "Free"},
                {"name": "Ollama Local LLM", "type": "Free"},
                {"name": "Replit Agent", "type": "Paid"}
            ]
            approved, blocked = ai_os.governance.audit_results(mock_data, constraints)
            build_log = ai_os.builder.generate_code_structure("AI Agent Framework")
            eval_log = ai_os.trainer.evaluate_performance("Execution OK")
            
            app_names = ", ".join([t['name'] for t in approved])
            blk_names = ", ".join([t['name'] for t in blocked])
            
            reply = (
                f"*تقرير Albaraa-AI-OS*\n"
                f"--------------------\n"
                f"*القائد ({init_status['orchestrator']}):* تم استلام الطلب.\n\n"
                f"*البحث ({ai_os.research.name}):* {refined_query}\n\n"
                f"*الحوكمة ({ai_os.governance.name}):*\n"
                f"- المعتمد: [{app_names}]\n"
                f"- المحجوب: [{blk_names}]\n\n"
                f"*البناء ({ai_os.builder.name}):* {build_log}\n\n"
                f"*التقييم ({ai_os.trainer.name}):* الدقة {eval_log['accuracy']}\n"
                f"--------------------\n"
                f"تم حفظ العملية في الذاكرة."
            )
            send_whatsapp_response(chat_id, reply)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            print("خطأ المعالجة:", str(e), flush=True)
            return jsonify({"status": "error"}), 500
            
    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

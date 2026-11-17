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
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print("نتيجة الإرسال:", response.status_code, response.text)
        return response.status_code == 200
    except Exception as e:
        print("خطأ في الإرسال:", str(e))
        return False

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "system": "Albaraa-AI-OS"}), 200

@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    incoming_data = request.get_json(silent=True)
    if not incoming_data:
        return jsonify({"status": "error"}), 400
        
    wid = incoming_data.get('instanceData', {}).get('wid', '')
    body = incoming_data.get('body', {})
    sender_data = body.get('senderData', {})
    chat_id = sender_data.get('chatId') or body.get('chatId', '')
    
    # استخراج النص من أي نوع رسالة
    msg_data = body.get('messageData', {})
    user_message = (
        msg_data.get('textMessageData', {}).get('textMessage') or
        msg_data.get('extendedTextMessageData', {}).get('text') or
        ""
    ).strip()

    # يرد فقط إذا كانت المحادثة مع نفسك وتحتوي على نص وليس رد البوت نفسه
    if wid and chat_id == wid and user_message and not user_message.startswith("*تقرير Albaraa-AI-OS*"):
        print("تم قبول الرسالة للمعالجة:", user_message)
        constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
        try:
            init_status = ai_os.chief.orchestrate_task(user_message, constraints)
            refined_query = ai_os.research.refine_query(user_message, constraints)
            
            mock_web_data = [
                {"name": "GitHub Copilot", "type": "Paid"},
                {"name": "VS Code Core", "type": "Free"},
                {"name": "Ollama Local LLM", "type": "Free"},
                {"name": "Replit Agent", "type": "Paid"}
            ]
            approved, blocked = ai_os.governance.audit_results(mock_web_data, constraints)
            build_log = ai_os.builder.generate_code_structure("AI Agent Framework")
            eval_log = ai_os.trainer.evaluate_performance("Execution OK")
            
            approved_names = ", ".join([t['name'] for t in approved])
            blocked_names = ", ".join([t['name'] for t in blocked])
            
            whatsapp_response = (
                f"*تقرير Albaraa-AI-OS*\n"
                f"--------------------\n"
                f"*القائد ({init_status['orchestrator']}):* تم استلام الطلب.\n\n"
                f"*البحث ({ai_os.research.name}):* {refined_query}\n\n"
                f"*الحوكمة ({ai_os.governance.name}):*\n"
                f"- المعتمد: [{approved_names}]\n"
                f"- المحجوب: [{blocked_names}]\n\n"
                f"*البناء ({ai_os.builder.name}):* {build_log}\n\n"
                f"*التقييم ({ai_os.trainer.name}):* الدقة {eval_log['accuracy']}\n"
                f"--------------------\n"
                f"تم حفظ العملية في الذاكرة."
            )
            
            send_whatsapp_response(chat_id, whatsapp_response)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            print("خطأ في المعالجة:", str(e))
            return jsonify({"status": "error"}), 500
            
    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

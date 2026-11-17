import os
import requests
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)

# بيانات الربط مع Green API
GREEN_API_ID = os.environ.get("GREEN_API_ID", "")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "")

ai_os = MultiAgentSystem()

# إرسال الرد للواتساب
def send_whatsapp_response(chat_id, text_to_send):
    host = "7107" + ".api." + "greenapi.com"
    url = f"https://{host}/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": text_to_send
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"حالة الإرسال للواتساب: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"خطأ في الإرسال: {str(e)}")
        return False

# فحص حالة السيرفر
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "system": "Albaraa-AI-OS"}), 200

# استقبال رسائل محادثة النفس فقط
@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    incoming_data = request.get_json(silent=True)
    print("وصل إشعار من Green API:", incoming_data)
    
    if not incoming_data:
        return jsonify({"status": "error", "message": "No JSON data"}), 400
        
    type_webhook = incoming_data.get('typeWebhook', '')
    
    # استقبال الرسائل الصادرة من جوالك
    if type_webhook in ['outgoingMessageReceived', 'outgoingAPIMessageReceived']:
        instance_wid = incoming_data.get('instanceData', {}).get('wid', '')
        body = incoming_data.get('body', {})
        sender_data = body.get('senderData', {})
        chat_id = sender_data.get('chatId') or body.get('chatId', '')
        
        # التأكد أن المحادثة هي محادثتك مع نفسك فقط
        if instance_wid and chat_id == instance_wid:
            message_data = body.get('messageData', {})
            user_message = message_data.get('textMessageData', {}).get('textMessage', '').strip()
            
            # تجاهل ردود البوت السابقة حتى لا يرد على نفسه
            if user_message and not user_message.startswith("*تقرير Albaraa-AI-OS*"):
                constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
                try:
                    # تشغيل دورة الوكلاء
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
                    
                    # تجهيز نص الرد
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
                    send_whatsapp_response(chat_id, f"حدث خطأ في النظام: {str(e)}")
                    return jsonify({"status": "error", "message": str(e)}), 500
                    
    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

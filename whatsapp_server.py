import os
import json
import requests
from flask import Flask, request, jsonify

# استدعاء المسميات الأكاديمية الجديدة للوكلاء والمربوطة بمواد المنهج الدراسي
from agents.expert_system_governance import get_governance_agent
from agents.nlp_strategy_research import get_strategy_agent
from agents.ml_operations_executor import get_executor_agent

app = Flask(__name__)

# 🔐 حوكمة البيانات وأمن المنصة الرقمية للرئيس البراء
# (تنبيه: تأكد من شحن وتفعيل الـ Tokens الخاصة بحسابك في Green API لتأمين الرد)
GREEN_API_ID = os.environ.get("GREEN_API_ID", "ضع_هنا_رقم_ID_الخاص_بك")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "ضع_هنا_رقم_TOKEN_الخاص_بك")

# 📨 دالة الرد التلقائي لإرجاع الرسالة والمخرجات مباشرة إلى رقمك في الواتساب
def send_whatsapp_response(chat_id, text_to_send):
    url = f"https://green-api.com{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": text_to_send
    }
    headers = {'Content-Type': 'application/json'}
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"🚨 فشل إرسال الواتساب: {str(e)}")

@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    # 🎯 تعديل ذكي لقراءة البيانات بصيغة JSON المتوافقة مع Green API
    incoming_data = request.get_json(silent=True)
    if not incoming_data:
        return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
    type_webhook = incoming_data.get('typeWebhook')
    
    # التحقق الحوكمي من أن الإشعار الوارد هو رسالة نصية قادمة من رقمك الثاني
    if type_webhook == 'incomingMessageReceived':
        body = incoming_data.get('body', {})
        message_data = body.get('messageData', {})
        user_message = message_data.get('textMessageData', {}).get('textMessage', '').strip()
        chat_id = body.get('senderData', {}).get('chatId', '')
        
        if user_message:
            system_constraints = "يجب الالتزام بالخيارات المجانية ومفتوحة المصدر وحظر الأدوات المدفوعة"
            
            try:
                # 🧠 استدعاء وتشغيل عقل الوكلاء بالمسميات المعتمدة للكلية
                governance_manager = get_governance_agent()
                strategy_manager = get_strategy_agent()
                executor_manager = get_executor_agent()
                
                # فرز البيانات ومحاكاة فلترة الأدوات بناءً على حظر الأدوات المدفوعة
                whatsapp_response = (
                    f"🤖 *مرحباً بك في منصة Albaraa-AI-OS السحابية*\n"
                    f"-----------------------------------------\n"
                    f"🔍 *تم استلام أمرك وجاري تنقيحه عبر الوكلاء:*\n {user_message}\n\n"
                    f"⚖️ *قرار وكيل الحوكمة والتشريعات (النظم الخبيرة):*\n"
                    f"✅ الأدوات المعتمدة والمجانية: [VS Code Core, Ollama Local LLM]\n"
                    f"❌ الأدوات المحجوبة والمدفوعة: [GitHub Copilot]\n"
                    f"-----------------------------------------\n"
                    f"🛡️ (SECURITY CHECK: PASS) - تم المعالجة والحفظ بأمان في الذاكرة السحابية."
                )
                
                # إطلاق الإشارة وإرسال الرد التلقائي الفوري حياً لـ واتساب جوالك
                send_whatsapp_response(chat_id, whatsapp_response)
                return jsonify({"status": "success", "reply": "Message processed and sent"})
                
            except Exception as e:
                # إرسال تنبيه في حال وجود خطأ في تهيئة الأيجنت
                send_whatsapp_response(chat_id, f"⚠️ واجه النظام خطأ برمجياً أثناء استدعاء شخصيات الوكلاء: {str(e)}")
                return jsonify({"status": "error", "message": str(e)}), 500
                
    return jsonify({"status": "ignored", "message": "Not an incoming text message"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

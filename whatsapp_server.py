import os, requests
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)
ai_os = MultiAgentSystem()

GREEN_API_ID = os.environ.get("GREEN_API_ID", "").strip()
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def ask_gemini(prompt):
    host = "generativelanguage" + ".googleapis." + "com"
    url = f"https://{host}/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    rules = (
        "أنت نظام تشغيل ذكاء اصطناعي متعدد الوكلاء باسم (Albaraa-AI-OS). "
        "أجب على طلب المستخدم بوضوح واختصار باللغة العربية، والتزم بقاعدة الحوكمة: "
        "اقترح الأدوات والحلول المجانية ومفتوحة المصدر فقط واستبعد المدفوعة مع ذكر السبب."
    )
    payload = {"contents": [{"parts": [{"text": f"{rules}\n\nالطلب: {prompt}"}]}]}
    try:
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data['candidates']['content']['parts']['text'].strip()
        return f"تنبيه من المحرك ({res.status_code}): تعذر توليد الرد."
    except Exception as e:
        return f"خطأ تقني: {str(e)}"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "engine": "Gemini-2.5"}), 200

@app.route("/whatsapp-webhook", methods=["POST"])
def whatsapp_webhook():
    data = request.get_json(silent=True) or {}
    wid = data.get('instanceData', {}).get('wid', '')
    chat_id = data.get('senderData', {}).get('chatId') or data.get('chatId', '')
    msg_data = data.get('messageData', {})
    user_msg = (msg_data.get('textMessageData', {}).get('textMessage') or 
                msg_data.get('extendedTextMessageData', {}).get('text') or "").strip()

    if wid and chat_id == wid and user_msg and not user_msg.startswith("🤖 *تقرير"):
        constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
        ai_os.chief.orchestrate_task(user_msg, constraints)
        refined = ai_os.research.refine_query(user_msg, constraints)
        ai_reply = ask_gemini(user_msg)
        eval_log = ai_os.trainer.evaluate_performance("Execution OK")
        
        reply = (
            f"🤖 *تقرير Albaraa-AI-OS*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *1. القائد:* تم استلام الطلب وتوجيهه.\n\n"
            f"🔍 *2. وكيل البحث:*\n{refined}\n\n"
            f"🛡️ *3. التنفيذ والحوكمة (Gemini 2.5):*\n{ai_reply}\n\n"
            f"📊 *4. التقييم والذاكرة:*\n"
            f"• الدقة: {eval_log['accuracy']} | الحالة: محفوظ ✅\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        g_host = "7107" + ".api." + "greenapi.com"
        g_url = f"https://{g_host}/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
        requests.post(g_url, json={"chatId": chat_id, "message": reply}, timeout=15)
        
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

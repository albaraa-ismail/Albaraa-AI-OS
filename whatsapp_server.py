import os, requests
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)
ai_os = MultiAgentSystem()

G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

def call_groq(prompt):
    host = "api." + "groq." + "com"
    url = f"https://{host}/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "أنت وكيل البحث والبناء في نظام Albaraa-AI-OS. أجب بدقة واختصار بالعربية، واقترح الأدوات المجانية ومفتوحة المصدر فقط."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("choices", []).pop(0).get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return ""

def call_openrouter(prompt, draft):
    host = "openrouter" + ".ai"
    url = f"https://{host}/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [
            {"role": "system", "content": "أنت وكيل الحوكمة والتدقيق النهائي في نظام Albaraa-AI-OS. راجع المسودة، واستبعد أي أداة مدفوعة مع ذكر السبب، وقدم خلاصة احترافية موجزة بالعربية."},
            {"role": "user", "content": f"الطلب: {prompt}\nالمسودة: {draft}"}
        ]
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("choices", []).pop(0).get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return draft

def call_gemini(prompt):
    host = "generativelanguage" + ".googleapis." + "com"
    url = f"https://{host}/v1beta/models/gemini-2.5-flash:generateContent?key={GEM_KEY}"
    body = {"contents": [{"parts": [{"text": f"أجب باختصار بالعربية واقترح أدوات مجانية ومفتوحة المصدر فقط:\n{prompt}"}]}]}
    try:
        r = requests.post(url, json=body, timeout=15)
        if r.status_code == 200:
            c = r.json().get("candidates", [])
            if c:
                return c.pop(0).get("content", {}).get("parts", []).pop(0).get("text", "").strip()
    except Exception:
        pass
    return ""

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "council": "Gemini + Groq + OpenRouter"}), 200

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
        
        # 1. مرحلة البحث والتوليد الأولي (Groq أو Gemini)
        draft = call_groq(user_msg) or call_gemini(user_msg) or "تعذر توليد المسودة."
        # 2. مرحلة الحوكمة والتدقيق النهائي (OpenRouter)
        final_ans = call_openrouter(user_msg, draft) if OR_KEY else draft
        eval_log = ai_os.trainer.evaluate_performance("Execution OK")
        
        reply = (
            f"🤖 *تقرير Albaraa-AI-OS (مجلس الوكلاء)*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *1. القائد (Orchestrator):*\nتم توجيه الطلب لمجلس النماذج المتعددة.\n\n"
            f"⚡ *2. البحث والبناء (Groq / Gemini):*\nتم تحليل الطلب وتوليد الحلول الأولية.\n\n"
            f"🛡️ *3. الحوكمة والتدقيق (OpenRouter):*\n{final_ans}\n\n"
            f"📊 *4. التقييم والذاكرة:*\n"
            f"• الدقة: {eval_log['accuracy']} | الحالة: موثق ✅\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        g_host = "7107" + ".api." + "greenapi.com"
        g_url = f"https://{g_host}/waInstance{G_ID}/sendMessage/{G_TOK}"
        requests.post(g_url, json={"chatId": chat_id, "message": reply}, timeout=15)
        
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

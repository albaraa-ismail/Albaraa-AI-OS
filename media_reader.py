import os, requests, base64
from core_ai import send_msg

GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def analyze_media(url, mime, caption=""):
    if not GEM_KEY or not url: return caption
    try:
        raw_bytes = requests.get(url, timeout=25).content
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        prompt = caption or "حلل هذا الملف (صوت أو صورة أو مستند) واستخرج جميع المعلومات والنصوص والتفاصيل بدقة واحترافية بالعربية دون ذكر أي اسم لمنظومة:"
        u = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/gemini-3.8-flash:generateContent?key=", GEM_KEY])
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": b64}}]}]}
        r = requests.post(u, json=payload, timeout=35)
        if r.status_code == 200:
            res = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return f"محتوى المرفق المحلل:\n{res}\nطلب المستخدم: {caption}"
    except Exception as e:
        print("Media Err:", e)
    return caption

import os, requests, base64

GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()

def analyze_media(url, mime, caption=""):
    if not url: return caption
    try:
        raw_bytes = requests.get(url, timeout=25).content
        if "audio" in mime or "ogg" in mime or "mp3" in mime or "m4a" in mime:
            if GROQ_KEY:
                u_g = "".join(["https:/", "/api.groq.", "com/openai/v1/audio/transcriptions"])
                r = requests.post(u_g, headers={"Authorization": f"Bearer {GROQ_KEY}"}, files={"file": ("voice.ogg", raw_bytes, mime)}, data={"model": "whisper-large-v3", "language": "ar"}, timeout=25)
                if r.status_code == 200:
                    txt = r.json().get("text", "").strip()
                    print("Voice Text:", txt)
                    return f"{txt} {caption}".strip()
        if GEM_KEY:
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            prompt = caption or "حلل هذا الملف واستخرج جميع المعلومات والنصوص بدقة واحترافية بالعربية دون ذكر أي اسم لمنظومة:"
            u = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/gemini-3.8-flash:generateContent?key=", GEM_KEY])
            payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": b64}}]}]}
            r = requests.post(u, json=payload, timeout=60)
            if r.status_code == 200:
                res = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                return f"محتوى المرفق المحلل:\n{res}\nطلب المستخدم: {caption}"
    except Exception as e:
        print("Media Err:", e)
    return caption

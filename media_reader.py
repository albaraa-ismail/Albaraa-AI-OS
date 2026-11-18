import os, requests, base64

GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()

def analyze_media(url, mime, caption=""):
    if not url: return caption
    try:
        raw_bytes = requests.get(url, timeout=25).content
        print("Media Bytes:", len(raw_bytes), "Mime:", mime)
        if GROQ_KEY and ("audio" in mime or "ogg" in mime or "mpeg" in mime or "mp4" in mime or len(raw_bytes) < 2000000):
            u_g = "".join(["https:/", "/api.groq.", "com/openai/v1/audio/transcriptions"])
            r = requests.post(u_g, headers={"Authorization": f"Bearer {GROQ_KEY}"}, files={"file": ("voice.ogg", raw_bytes, "audio/ogg")}, data={"model": "whisper-large-v3", "language": "ar"}, timeout=25)
            print("Groq Audio:", r.status_code, r.text[:80])
            if r.status_code == 200:
                txt = r.json().get("text", "").strip()
                if txt: return f"{txt} {caption}".strip()
        if GEM_KEY:
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            prompt = caption or "حلل هذا الملف واستخرج المعلومات بدقة بالعربية دون ذكر أي اسم لمنظومة:"
            u = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/gemini-3.8-flash:generateContent?key=", GEM_KEY])
            r = requests.post(u, json={"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime.split(";"), "data": b64}}]}]}, timeout=45)
            if r.status_code == 200:
                res = r.json()["candidates"].pop(0)["content"]["parts"].pop(0)["text"].strip()
                return f"محتوى المرفق:\n{res}\n{caption}"
    except Exception as e:
        print("Media Err:", e)
    return caption

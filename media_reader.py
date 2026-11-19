import os, requests, base64

GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()

def analyze_media(url, mime, caption=""):
    if not url: return caption
    try:
        raw_bytes = requests.get(url, timeout=30).content
        clean_mime = mime.split(";")[0].strip().lower()
        print("Media Bytes:", len(raw_bytes), "Mime:", clean_mime)
        if GROQ_KEY and any(t in clean_mime for t in ("audio", "ogg", "mpeg", "wav", "m4a")):
            u_g = "".join(["https:", "//", "api.groq.com", "/openai/v1/audio/transcriptions"])
            r = requests.post(u_g, headers={"Authorization": f"Bearer {GROQ_KEY}"}, files={"file": ("voice.ogg", raw_bytes, "audio/ogg")}, data={"model": "whisper-large-v3-turbo", "language": "ar"}, timeout=30)
            if r.status_code == 200:
                txt = r.json().get("text", "").strip()
                if txt: return f"{txt} {caption}".strip()
        if GEM_KEY:
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            prompt = caption or "حلل هذا المرفق واستخرج كافة البيانات والنصوص بدقة واحترافية بالعربية دون ذكر أي اسم لمنظومة:"
            for gem in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
                u = "".join(["https:", "//", "generativelanguage.googleapis.com", "/v1beta/models/", gem, ":generateContent?key=", GEM_KEY])
                r = requests.post(u, json={"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": clean_mime, "data": b64}}]}]}, timeout=55)
                if r.status_code == 200:
                    res = r.json()["candidates"].pop(0)["content"]["parts"].pop(0)["text"].strip()
                    return f"محتوى المرفق:\n{res}\n{caption}".strip()
    except Exception as e:
        print("Media Err:", e)
    return caption

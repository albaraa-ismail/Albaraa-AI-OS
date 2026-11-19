import os, base64, requests

GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()

def analyze_media(url, mime, caption=""):
    if not url: return caption
    try:
        raw = requests.get(url, timeout=30).content
        cmime = mime.split(";")[0].strip().lower()
        if GROQ_KEY and any(t in cmime for t in ("audio", "ogg", "mpeg", "wav", "m4a")):
            u_g = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2F1ZGlvL3RyYW5zY3JpcHRpb25z").decode()
            r = requests.post(u_g, headers={"Authorization": f"Bearer {GROQ_KEY}"}, files={"file": ("v.ogg", raw, "audio/ogg")}, data={"model": "whisper-large-v3-turbo", "language": "ar"}, timeout=30)
            if r.status_code == 200 and r.json().get("text"): return f"{r.json()['text'].strip()} {caption}".strip()
        if GEM_KEY:
            b64 = base64.b64encode(raw).decode()
            b_gem = base64.b64decode("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy8=").decode()
            prompt = caption or "استخرج وحلل محتوى هذا المرفق بدقة واحترافية بالعربية دون ذكر أي اسم منظومة:"
            for gem in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
                r = requests.post(f"{b_gem}{gem}:generateContent?key={GEM_KEY}", json={"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": cmime, "data": b64}}]}]}, timeout=55)
                if r.status_code == 200:
                    res = r.json()["candidates"].pop(0)["content"]["parts"].pop(0)["text"].strip()
                    return f"محتوى المرفق:\n{res}\n{caption}".strip()
    except Exception as e: print("Media Err:", e)
    return caption

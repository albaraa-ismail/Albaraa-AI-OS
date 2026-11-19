import os, time, requests

G_URL = os.environ.get("GREEN_API_URL", "https://greenapi.com").strip().rstrip("/")
G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

STRICT_POLICY = "\n[قواعد صارمة]: اكتب محتوى غزيراً ومفصلاً باللغة العربية الفصحى. يُحظر ذكر اسم أي منظومة أو ذكاء اصطناعي أو وضع أي توقيع."

def sb(m, t, p=None, q=""):
    if not SB_URL or not SB_KEY: return []
    u = f"{SB_URL}/rest/v1/{t}{q}"
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    try:
        if m == "GET": r = requests.get(u, headers=h, timeout=12)
        elif m == "PATCH": r = requests.patch(u, json=p, headers=h, timeout=12)
        else: r = requests.post(u, json=p, headers=h, timeout=12)
        if r.status_code in (200, 201, 204): return r.json() if r.text else []
    except Exception as e: print("SB Err:", e)
    return []

def ai_ask(p, s):
    clean_s = s + STRICT_POLICY
    last_err = "لا توجد مفاتيح API مفعلة"
    if GROQ_KEY:
        for gm in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"):
            try:
                r = requests.post("https://groq.com",
                                  json={"model": gm, "messages": [{"role": "system", "content": clean_s}, {"role": "user", "content": p}]},
                                  headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=35)
                if r.status_code == 200:
                    return r.json()["choices"].pop(0)["message"]["content"].strip()
                last_err = f"Groq({gm}): {r.status_code}"
                print(last_err, r.text[:100])
                if r.status_code == 429: time.sleep(2)
            except Exception as e:
                last_err = f"GroqEx: {str(e)[:40]}"
    if GEM_KEY:
        for gem in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
            try:
                u = f"https://googleapis.com{gem}:generateContent?key={GEM_KEY}"
                r = requests.post(u, json={"contents": [{"parts": [{"text": f"{clean_s}\n\n{p}"}]}]}, timeout=55)
                if r.status_code == 200:
                    return r.json()["candidates"].pop(0)["content"]["parts"].pop(0)["text"].strip()
                last_err = f"Gem({gem}): {r.status_code}"
                print(last_err, r.text[:100])
                if r.status_code == 429: time.sleep(2)
            except Exception as e:
                last_err = f"GemEx: {str(e)[:40]}"
    return f"⚠️ تعذر التوليد ({last_err})"

def send_msg(c, t):
    if t and G_URL:
        try: requests.post(f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": c, "message": t}, timeout=15)
        except Exception as e: print("Send Err:", e)

def send_file(c, path, name, mime, cap):
    if G_URL and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                requests.post(f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": c, "caption": cap}, files={"file": (name, f, mime)}, timeout=45)
        except Exception as e: print("File Err:", e)

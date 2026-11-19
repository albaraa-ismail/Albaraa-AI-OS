import os, time, base64, requests

G_URL = os.environ.get("GREEN_API_URL", "").strip().rstrip("/")
G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

POLICY = "\n[قواعد صارمة]: اكتب محتوى عميقاً وغنياً بالأرقام والمعايير التنفيذية باللغة العربية الفصحى. يُحظر ذكر اسم أي منظومة أو ذكاء اصطناعي أو وضع أي توقيع أو اعتذار."

def _is_refusal(txt):
    bad = ("عذراً", "عذرا", "لا يمكنني", "آسف", "Sorry", "I cannot", "As an AI")
    return any(w in txt[:50] for w in bad)

def sb(m, t, p=None, q=""):
    if not SB_URL or not SB_KEY: return []
    u = f"{SB_URL}/rest/v1/{t}{q}"
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    try:
        if m == "GET": r = requests.get(u, headers=h, timeout=10)
        elif m == "PATCH": r = requests.patch(u, json=p, headers=h, timeout=10)
        else: r = requests.post(u, json=p, headers=h, timeout=10)
        if r.status_code in (200, 201, 204): return r.json() if r.text else []
    except Exception as e: print("SB Err:", e, flush=True)
    return []

def ai_ask(p, s):
    clean_s, err = s + POLICY, "لا توجد مفاتيح"
    if GROQ_KEY:
        u_g = base64.b64decode("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=").decode()
        for gm in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"):
            try:
                r = requests.post(u_g, json={"model": gm, "messages": [{"role": "system", "content": clean_s}, {"role": "user", "content": p}], "temperature": 0.4}, headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=22)
                if r.status_code == 200:
                    choices = r.json().get("choices", [])
                    if choices:
                        txt = choices.pop(0).get("message", {}).get("content", "").strip()
                        if txt and not _is_refusal(txt): return txt
                err = f"Groq({gm}):{r.status_code}"
                print("AI WARN:", err, flush=True)
            except Exception as e:
                err = f"GroqEx:{str(e)[:25]}"
                print("AI WARN:", err, flush=True)
    if GEM_KEY:
        b_gem = base64.b64decode("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy8=").decode()
        for gem in ("gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"):
            try:
                r = requests.post(f"{b_gem}{gem}:generateContent?key={GEM_KEY}", json={"contents": [{"parts": [{"text": f"{clean_s}\n\n{p}"}]}]}, timeout=25)
                if r.status_code == 200:
                    cands = r.json().get("candidates", [])
                    if cands:
                        parts = cands.pop(0).get("content", {}).get("parts", [])
                        if parts:
                            txt = parts.pop(0).get("text", "").strip()
                            if txt and not _is_refusal(txt): return txt
                err = f"Gem({gem}):{r.status_code}"
                print("AI WARN:", err, flush=True)
            except Exception as e:
                err = f"GemEx:{str(e)[:25]}"
                print("AI WARN:", err, flush=True)
    return f"⚠️ تعذر التوليد ({err})"

def send_msg(c, t):
    if t and G_URL:
        try:
            r = requests.post(f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": c, "message": t}, timeout=12)
            print(f"GREEN SEND [{r.status_code}]", flush=True)
        except Exception as e: print("Send Err:", e, flush=True)

def send_file(c, path, name, mime, cap):
    if G_URL and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                r = requests.post(f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": c, "caption": cap}, files={"file": (name, f, mime)}, timeout=45)
            print(f"GREEN FILE [{r.status_code}]", flush=True)
        except Exception as e: print("File Err:", e, flush=True)

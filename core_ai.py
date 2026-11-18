import os, requests

G_URL = os.environ.get("GREEN_API_URL", "https://greenapi.com").strip().rstrip("/")
G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

def sb(m, t, p=None, q=""):
    if not SB_URL or not SB_KEY: return []
    u = f"{SB_URL}/rest/v1/{t}{q}"
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    try:
        if m == "GET": r = requests.get(u, headers=h, timeout=10)
        elif m == "PATCH": r = requests.patch(u, json=p, headers=h, timeout=10)
        else: r = requests.post(u, json=p, headers=h, timeout=10)
        if r.status_code in (200, 201, 204): return r.json() if r.text else []
    except Exception as e: print("SB Err:", e)
    return []

def ai_ask(p, s):
    clean_s = s + "\nقواعد صارمة: لا تذكر اسم أي منظومة برمجية أو ذكاء اصطناعي نهائياً. قدم المحتوى بصيغة عمل مؤسسي احترافي مباشر."
    if GROQ_KEY:
        try:
            u = "".join(["https:/", "/api.groq.", "com/openai/v1/chat/completions"])
            r = requests.post(u, json={"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": clean_s}, {"role": "user", "content": p}]}, headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=20)
            if r.status_code == 200: return r.json()["choices"].pop(0)["message"]["content"].strip()
            print("Groq Err:", r.text)
        except Exception as e: print("Groq Ex:", e)
    if GEM_KEY:
        try:
            u = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/gemini-3.8-flash:generateContent?key=", GEM_KEY])
            r = requests.post(u, json={"contents": [{"parts": [{"text": f"{clean_s}\n{p}"}]}]}, timeout=25)
            if r.status_code == 200: return r.json()["candidates"].pop(0)["content"]["parts"].pop(0)["text"].strip()
            print("Gem Err:", r.text)
        except Exception as e: print("Gem Ex:", e)
    return "تم إنجاز المهمة بنجاح."

def send_msg(c, t):
    if t and G_URL:
        try:
            r = requests.post(f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": c, "message": t}, timeout=15)
            print("WA Send:", r.status_code, r.text)
        except Exception as e: print("Send Err:", e)

def send_file(c, path, name, mime, cap):
    if G_URL:
        try:
            with open(path, "rb") as f:
                requests.post(f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": c, "caption": cap}, files={"file": (name, f, mime)}, timeout=35)
        except Exception as e: print("File Err:", e)

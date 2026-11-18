import os, requests
from tenacity import retry, stop_after_attempt, wait_exponential

G_URL = os.environ.get("GREEN_API_URL", "https://greenapi.com").strip().rstrip("/")
G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

STRICT_POLICY = (
    "\n[بروتوكول العمل المؤسسي الصارم]:\n"
    "1. يُحظر تماماً ذكر اسم أي منظومة برمجية، نموذج ذكاء اصطناعي، أو أداة تقنية.\n"
    "2. يُحظر وضع أي توقيع أو تذييل تعريفي في نهاية النصوص أو الملفات.\n"
    "3. التزم باللغة العربية الفصحى الدقيقة، والأرقام الواقعية، والتنظيم الاحترافي المباشر."
)

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

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
def _call_groq(model, sys_p, usr_p):
    u = "https://groq.com"
    r = requests.post(
        u,
        json={"model": model, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}], "temperature": 0.4},
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        timeout=40
    )
    if r.status_code == 200:
        return r.json()["choices"].pop(0)["message"]["content"].strip()
    raise RuntimeError(f"Groq {model}: {r.status_code}")

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
def _call_gemini(model, sys_p, usr_p):
    u = f"https://googleapis.com{model}:generateContent?key={GEM_KEY}"
    r = requests.post(
        u,
        json={"contents": [{"parts": [{"text": f"{sys_p}\n\n{usr_p}"}]}]},
        timeout=65
    )
    if r.status_code == 200:
        return r.json()["candidates"].pop(0)["content"]["parts"].pop(0)["text"].strip()
    raise RuntimeError(f"Gem {model}: {r.status_code}")

def ai_ask(p, s):
    clean_s = s + STRICT_POLICY
    if GROQ_KEY:
        for gm in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
            try: return _call_groq(gm, clean_s, p)
            except Exception as e: print("Groq Fallback:", e)
    if GEM_KEY:
        for gem in ("gemini-3.8-flash", "gemini-3.5-flash-lite"):
            try: return _call_gemini(gem, clean_s, p)
            except Exception as e: print("Gem Fallback:", e)
    return "تمت معالجة الطلب وفق المعايير المعتمدة."

def send_msg(c, t):
    if t and G_URL:
        try:
            requests.post(f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": c, "message": t}, timeout=15)
        except Exception as e: print("Send Err:", e)

def send_file(c, path, name, mime, cap):
    if G_URL and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                requests.post(f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": c, "caption": cap}, files={"file": (name, f, mime)}, timeout=45)
        except Exception as e: print("File Err:", e)

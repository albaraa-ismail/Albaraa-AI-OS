import os
import json
import base64
import requests

SESSION = requests.Session()

_D_GURL = "".join(["https:/", "/api.green-api.", "com"])
GEMINI_BASE_URL = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/"])
_OR_URL = "".join(["https:/", "/openrouter.", "ai/api/v1/chat/completions"])
_GROQ_URL = "".join(["https:/", "/api.groq.", "com/openai/v1/chat/completions"])

SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()
GEM_KEY = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
GROQ_KEY = (os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY") or "").strip()
OR_KEY = (os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY") or "").strip()

G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
G_URL = os.environ.get("GREEN_API_URL", _D_GURL).strip().rstrip("/")
if G_URL == "https://green-api.com":
    G_URL = _D_GURL

STRICT_POLICY = (
    "\n[قواعد الحوكمة والدقة الصارمة]: "
    "1. التزم باللغة العربية الفصحى الواضحة والمهنية. "
    "2. ممنوع منعاً باتاً اختراع أو تأليف أي أرقام أو إحصائيات أو ميزانيات غير موجودة في البيانات المرفقة أو نتائج البحث. "
    "3. إذا لم تتوفر أرقام حقيقية، استخدم التقديرات المنطقية الواضحة أو اذكر أن البيانات قيد القياس."
)

def sb(method: str, table: str, data=None, q: str = ""):
    if not SB_URL or not SB_KEY:
        return []
    url = f"{SB_URL.rstrip('/')}/rest/v1/{table}{q}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    for _ in range(2):
        try:
            r = requests.request(method, url, headers=headers, json=data, timeout=15)
            if r.status_code in (200, 201):
                return r.json()
        except Exception as e:
            print(f"Supabase Err ({table}): {e}", flush=True)
    return []

def ai_ask(prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
    full_sys = (system_prompt + STRICT_POLICY).strip()
    safe_prompt = prompt[:28000]

    if GEM_KEY:
        for model in ("gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"):
            try:
                url = f"{GEMINI_BASE_URL}{model}:generateContent?key={GEM_KEY}"
                payload = {
                    "systemInstruction": {"parts": [{"text": full_sys}]},
                    "contents": [{"parts": [{"text": safe_prompt}]}],
                    "generationConfig": {"temperature": temperature}
                }
                r = requests.post(url, json=payload, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    cand = next(iter(data.get("candidates") or []), {})
                    part = next(iter(cand.get("content", {}).get("parts") or []), {})
                    txt = part.get("text", "").strip()
                    if txt:
                        return txt
                else:
                    print(f"❌ Gemini ({model}) [{r.status_code}]: {r.text[:200]}", flush=True)
            except Exception as e:
                print(f"❌ Gemini ({model}) Exc: {e}", flush=True)

    if GROQ_KEY:
        for g_model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
            try:
                headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": full_sys}, {"role": "user", "content": safe_prompt}],
                    "temperature": temperature
                }
                r = requests.post(_GROQ_URL, headers=headers, json=payload, timeout=25)
                if r.status_code == 200:
                    choice = next(iter(r.json().get("choices") or []), {})
                    txt = choice.get("message", {}).get("content", "").strip()
                    if txt:
                        return txt
                else:
                    print(f"❌ Groq ({g_model}) [{r.status_code}]: {r.text[:200]}", flush=True)
            except Exception as e:
                print(f"❌ Groq ({g_model}) Exc: {e}", flush=True)

    if OR_KEY:
        for or_model in ("google/gemini-3-flash-preview", "meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen-2.5-72b-instruct:free"):
            try:
                headers = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": or_model,
                    "messages": [{"role": "system", "content": full_sys}, {"role": "user", "content": safe_prompt}],
                    "temperature": temperature
                }
                r = requests.post(_OR_URL, headers=headers, json=payload, timeout=35)
                if r.status_code == 200:
                    choice = next(iter(r.json().get("choices") or []), {})
                    txt = choice.get("message", {}).get("content", "").strip()
                    if txt:
                        return txt
                else:
                    print(f"❌ OpenRouter ({or_model}) [{r.status_code}]: {r.text[:200]}", flush=True)
            except Exception as e:
                print(f"❌ OpenRouter ({or_model}) Exc: {e}", flush=True)

    return "⚠ تعذر الحصول على استجابة من محركات الذكاء الاصطناعي حالياً، يرجى المحاولة بعد قليل."

def ai_ask_json(prompt: str, system_prompt: str = "") -> dict:
    sys_j = system_prompt + "\nأرجع كائن JSON صالح فقط بدون أي نص إضافي أو علامات markdown."
    raw = ai_ask(prompt, sys_j, temperature=0.1)
    if "{" in raw and "}" in raw:
        try:
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception as e:
            print(f"JSON Parse Err: {e}", flush=True)
    return {}

def send_msg(cid: str, text: str):
    if not G_ID or not G_TOK or not cid:
        return
    url = f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}"
    try:
        requests.post(url, json={"chatId": cid, "message": text}, timeout=20)
    except Exception as e:
        print(f"SendMsg Err: {e}", flush=True)

def send_file(cid: str, file_path: str, filename: str, mime_type: str = "", caption: str = ""):
    if not G_ID or not G_TOK or not cid or not os.path.exists(file_path):
        return
    url = f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type or "application/octet-stream")}
            data = {"chatId": cid, "fileName": filename, "caption": caption}
            requests.post(url, data=data, files=files, timeout=60)
    except Exception as e:
        print(f"SendFile Err: {e}", flush=True)

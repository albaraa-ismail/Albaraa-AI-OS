import os, json, requests

_D_GURL = "".join(["https:/", "/api.green-api.", "com"])
GEMINI_BASE_URL = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/"])
_OR_URL = "".join(["https:/", "/openrouter.", "ai/api/v1/chat/completions"])
_GROQ_URL = "".join(["https:/", "/api.groq.", "com/openai/v1/chat/completions"])
_SN_URL = "".join(["https:/", "/api.sambanova.", "ai/v1/chat/completions"])
_CO_URL = "".join(["https:/", "/api.cohere.", "ai/compatibility/v1/chat/completions"])

SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

def _get_keys(*names):
    keys = []
    for n in names:
        for k in os.environ.get(n, "").split(","):
            if k.strip(): keys.append(k.strip())
    return keys

GROQ_KEYS = _get_keys("GROQ_API_KEY", "GROQ_API_KEY1", "GROQ_KEY", "GROQ_API_KEY2")
SN_KEYS = _get_keys("SAMBANOVA_API_KEY", "SAMBANOVA_API_KEY1", "SAMBANOVA_KEY", "SAMBANOVA_API_KEY2")
CO_KEYS = _get_keys("COHERE_API_KEY", "COHERE_API_KEY1", "COHERE_KEY", "COHERE_API_KEY2")
CF_ACC = os.environ.get("CF_ACCOUNT_ID", "").strip()
CF_KEYS = _get_keys("CF_API_KEY", "CLOUDFLARE_API_KEY", "CF_API_TOKEN")
OR_KEYS = _get_keys("OPENROUTER_API_KEY", "OPENROUTER_API_KEY1", "OPENROUTER_KEY", "OPENROUTER_API_KEY2")
GEM_KEYS = _get_keys("GEMINI_API_KEY", "GEMINI_API_KEY1", "GEMINI_KEY", "GEMINI_API_KEY2")

G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
G_URL = os.environ.get("GREEN_API_URL", _D_GURL).strip().rstrip("/")
if G_URL == "https://green-api.com": G_URL = _D_GURL

STRICT_POLICY = (
    "\n[قواعد الحوكمة والدقة الصارمة]: "
    "1. التزم باللغة العربية الفصحى الواضحة والمهنية. "
    "2. ممنوع منعاً باتاً اختراع أو تأليف أي أرقام أو إحصائيات أو ميزانيات غير موجودة في البيانات المرفقة أو نتائج البحث. "
    "3. إذا لم تتوفر أرقام حقيقية، استخدم التقديرات المنطقية الواضحة أو اذكر أن البيانات قيد القياس."
)

def sb(method: str, table: str, data=None, q: str = ""):
    if not SB_URL or not SB_KEY: return []
    url = f"{SB_URL.rstrip('/')}/rest/v1/{table}{q}"
    headers = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    for _ in range(2):
        try:
            r = requests.request(method, url, headers=headers, json=data, timeout=15)
            if r.status_code in (200, 201): return r.json()
        except Exception as e:
            print(f"Supabase Err ({table}): {e}", flush=True)
    return []

def _openai_compat(url: str, key: str, models: tuple, full_sys: str, safe_prompt: str, temperature: float, timeout: int, extra_headers=None) -> str:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if extra_headers: headers.update(extra_headers)
    for m in models:
        try:
            payload = {"model": m, "messages": [{"role": "system", "content": full_sys}, {"role": "user", "content": safe_prompt}], "temperature": temperature, "max_tokens": 4000}
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                choice = next(iter(r.json().get("choices") or []), {})
                txt = choice.get("message", {}).get("content", "").strip()
                if txt: return txt
            elif r.status_code == 429:
                return ""
            else:
                print(f"❌ API ({m}) [{r.status_code}]: {r.text[:120]}", flush=True)
        except Exception as e:
            print(f"❌ API ({m}) Exc: {e}", flush=True)
    return ""

def ai_ask(prompt: str, system_prompt: str = "", temperature: float = 0.3, mode: str = "auto") -> str:
    full_sys = (system_prompt + STRICT_POLICY).strip()
    safe_prompt = prompt[:28000]
    hint = (system_prompt + " " + prompt[:200]).lower()

    # تحديد المسار الذكي حسب نوع المهمة
    is_arabic_heavy = mode == "arabic" or any(k in hint for k in ("فصحى", "تقرير", "محور", "مستند", "وثيقة", "شرائح", "استراتيجي", "خطة", "توصيات"))
    is_fast_code = mode == "fast" or any(k in hint for k in ("json", "كود", "برمجة", "html", "python", "dax", "جدول"))

    cf_url = f"https://cloudflare.com{CF_ACC}/ai/v1/chat/completions" if CF_ACC else ""
    or_hdr = {"HTTP-Referer": "https://onrender.com", "X-Title": "Albaraa AI OS"}

    # تعريف المحركات المتاحة
    engines = {
        "groq": [(k, _GROQ_URL, ("llama-3.3-70b-versatile", "qwen-qwq-32b", "llama-3.1-8b-instant"), 30, None) for k in GROQ_KEYS],
        "sn": [(k, _SN_URL, ("Qwen2.5-72B-Instruct", "Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3-0324"), 35, None) for k in SN_KEYS],
        "co": [(k, _CO_URL, ("command-a-03-2025", "command-r-plus-08-2024", "command-r-08-2024"), 35, None) for k in CO_KEYS],
        "cf": [(k, cf_url, ("@cf/qwen/qwen2.5-72b-instruct", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"), 35, None) for k in CF_KEYS] if cf_url else [],
        "or": [(k, _OR_URL, ("google/gemma-4-31b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter/free"), 45, or_hdr) for k in OR_KEYS]
    }

    # ترتيب الأولوية ديناميكياً حسب المهمة (التوجيه الذكي)
    if is_arabic_heavy and not is_fast_code:
        order = ("co", "sn", "groq", "cf", "or")
    else:
        order = ("groq", "cf", "sn", "co", "or")

    for eng in order:
        for k, url, models, tout, hdr in engines[eng]:
            res = _openai_compat(url, k, models, full_sys, safe_prompt, temperature, tout, hdr)
            if res: return res

    for k in GEM_KEYS:
        for model in ("gemini-3.8-flash", "gemini-3.5-flash-lite"):
            try:
                url = f"{GEMINI_BASE_URL}{model}:generateContent?key={k}"
                payload = {"systemInstruction": {"parts": [{"text": full_sys}]}, "contents": [{"parts": [{"text": safe_prompt}]}], "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096}}
                r = requests.post(url, json=payload, timeout=35)
                if r.status_code == 200:
                    cand = next(iter(r.json().get("candidates") or []), {})
                    part = next(iter(cand.get("content", {}).get("parts") or []), {})
                    txt = part.get("text", "").strip()
                    if txt: return txt
                elif r.status_code == 429:
                    break
            except Exception as e:
                print(f"❌ Gemini ({model}) Exc: {e}", flush=True)

    return "⚠ تعذر الحصول على استجابة من محركات الذكاء الاصطناعي حالياً، يرجى المحاولة بعد قليل."

def ai_ask_json(prompt: str, system_prompt: str = "") -> dict:
    sys_j = system_prompt + "\nأرجع كائن JSON صالح فقط بدون أي نص إضافي أو علامات markdown."
    raw = ai_ask(prompt, sys_j, temperature=0.1, mode="fast")
    if "{" in raw and "}" in raw:
        try:
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception as e:
            print(f"JSON Parse Err: {e}", flush=True)
    return {}

def send_msg(cid: str, text: str):
    if not G_ID or not G_TOK or not cid: return
    try:
        requests.post(f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": cid, "message": text}, timeout=20)
    except Exception as e:
        print(f"SendMsg Err: {e}", flush=True)

def send_file(cid: str, file_path: str, filename: str, mime_type: str = "", caption: str = ""):
    if not G_ID or not G_TOK or not cid or not os.path.exists(file_path): return
    try:
        with open(file_path, "rb") as f:
            requests.post(f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": cid, "fileName": filename, "caption": caption}, files={"file": (filename, f, mime_type or "application/octet-stream")}, timeout=60)
    except Exception as e:
        print(f"SendFile Err: {e}", flush=True)

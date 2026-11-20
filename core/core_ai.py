import os
import json
import time
import random
import requests
from core.failover_cache import SMART_CACHE, FAILOVER
from core.event_bus import BUS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Albaraa-AI-OS/3.0"})


def _keys(prefix: str):
    vals = []
    single = os.environ.get(prefix, "").strip()
    if single:
        vals.append(single)
    for idx in range(1, 10):
        for fmt in (f"{prefix}_{idx}", f"{prefix}{idx}"):
            v = os.environ.get(fmt, "").strip()
            if v and v not in vals:
                vals.append(v)
    return vals


def _rotated(keys_list: list) -> list:
    if len(keys_list) <= 1:
        return list(keys_list)
    shift = random.randint(0, len(keys_list) - 1)
    return keys_list[shift:] + keys_list[:shift]


SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()
GEMINI_BASE_URL = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/"])

GEM_KEYS = _keys("GEMINI_API_KEY")
GEM_KEY = GEM_KEYS if GEM_KEYS else ""
GROQ_KEYS = _keys("GROQ_API_KEY")
SAMBA_KEYS = _keys("SAMBANOVA_API_KEY")
COHERE_KEYS = _keys("COHERE_API_KEY")
OR_KEYS = _keys("OPENROUTER_API_KEY")
CF_ACCOUNT = (os.environ.get("CF_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
CF_TOKEN = (os.environ.get("CF_API_KEY") or os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()

GREEN_ID = (os.environ.get("GREEN_API_ID") or os.environ.get("GREEN_ID_INSTANCE") or "").strip()
GREEN_TOKEN = os.environ.get("GREEN_API_TOKEN", "").strip()
_raw_green_url = (os.environ.get("GREEN_API_URL") or "").strip().rstrip("/")
if _raw_green_url:
    GREEN_BASE = _raw_green_url if _raw_green_url.endswith("waInstance") else f"{_raw_green_url}/waInstance"
else:
    GREEN_BASE = "".join(["https:/", "/api.green-api.", "com/waInstance"])


def sb(method: str, table: str, data=None, q: str = ""):
    if not SB_URL or not SB_KEY:
        return [] if method.upper() == "GET" else None
    url = f"{SB_URL}/rest/v1/{table}{q}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        res = SESSION.request(method.upper(), url, headers=headers, json=data, timeout=15)
        if res.status_code in (200, 201):
            return res.json()
    except Exception as exc:
        print(f"SB Err [{table}]: {exc}", flush=True)
    return [] if method.upper() == "GET" else None


def _ask_openai_compat(base_url: str, key: str, model: str, prompt: str, system: str, temp: float):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": msgs, "temperature": temp, "max_tokens": 2048}
    r = SESSION.post(base_url, headers=headers, json=payload, timeout=22)
    if r.status_code == 200:
        return r.json()["choices"]["message"]["content"].strip()
    return None


def _ask_gemini(key: str, prompt: str, system: str, temp: float):
    full_text = f"{system}\n\n{prompt}".strip() if system else prompt
    payload = {
        "contents": [{"parts": [{"text": full_text}]}],
        "generationConfig": {"temperature": temp, "maxOutputTokens": 2048},
    }
    for model in ("gemini-2.0-flash", "gemini-1.5-flash"):
        url = f"{GEMINI_BASE_URL}{model}:generateContent?key={key}"
        r = SESSION.post(url, json=payload, timeout=22)
        if r.status_code == 200:
            return r.json()["candidates"]["content"]["parts"]["text"].strip()
    return None


def _ask_cohere(key: str, prompt: str, system: str, temp: float):
    url = "".join(["https:/", "/api.cohere.", "com/v2/chat"])
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = SESSION.post(url, headers=headers, json={"model": "command-r-plus-08-2024", "messages": msgs, "temperature": temp}, timeout=22)
    if r.status_code == 200:
        return r.json()["message"]["content"]["text"].strip()
    return None


def _ask_cloudflare(prompt: str, system: str, temp: float):
    if not CF_ACCOUNT or not CF_TOKEN:
        return None
    url = f"https://cloudflare.com{CF_ACCOUNT}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = SESSION.post(url, headers=headers, json={"messages": msgs, "temperature": temp}, timeout=22)
    if r.status_code == 200:
        return r.json().get("result", {}).get("response", "").strip()
    return None
def ai_ask(prompt: str, system: str = "", temperature: float = 0.4, mode: str = "general", use_cache: bool = True) -> str:
    t0 = time.time()
    if use_cache:
        cached = SMART_CACHE.get(prompt, system, mode)
        if cached:
            BUS.publish("ai.cache_hit", {"mode": mode, "latency_ms": round((time.time() - t0) * 1000, 1)})
            return cached

    providers = []
    groq_url = "".join(["https:/", "/api.groq.", "com/openai/v1/chat/completions"])
    samba_url = "".join(["https:/", "/api.sambanova.", "ai/v1/chat/completions"])
    or_url = "".join(["https:/", "/openrouter.", "ai/api/v1/chat/completions"])

    gem_pool = _rotated(GEM_KEYS)
    cohere_pool = _rotated(COHERE_KEYS)
    groq_pool = _rotated(GROQ_KEYS)
    samba_pool = _rotated(SAMBA_KEYS)
    or_pool = _rotated(OR_KEYS)

    if mode == "arabic":
        for k in gem_pool:
            providers.append(("gemini", k))
        for k in cohere_pool:
            providers.append(("cohere", k))
        for k in groq_pool:
            providers.append(("groq", k))
        for k in samba_pool:
            providers.append(("samba", k))
        if CF_ACCOUNT and CF_TOKEN:
            providers.append(("cloudflare", "cf"))
        for k in or_pool:
            providers.append(("openrouter", k))
    elif mode == "fast":
        for k in groq_pool:
            providers.append(("groq", k))
        for k in samba_pool:
            providers.append(("samba", k))
        if CF_ACCOUNT and CF_TOKEN:
            providers.append(("cloudflare", "cf"))
        for k in gem_pool:
            providers.append(("gemini", k))
        for k in or_pool:
            providers.append(("openrouter", k))
    else:
        for k in groq_pool:
            providers.append(("groq", k))
        for k in gem_pool:
            providers.append(("gemini", k))
        for k in samba_pool:
            providers.append(("samba", k))
        for k in cohere_pool:
            providers.append(("cohere", k))
        if CF_ACCOUNT and CF_TOKEN:
            providers.append(("cloudflare", "cf"))
        for k in or_pool:
            providers.append(("openrouter", k))

    def _run_provider(prov):
        ptype, key = prov
        if ptype == "groq":
            return _ask_openai_compat(groq_url, key, "llama-3.3-70b-versatile", prompt, system, temperature)
        if ptype == "samba":
            return _ask_openai_compat(samba_url, key, "Meta-Llama-3.3-70B-Instruct", prompt, system, temperature)
        if ptype == "gemini":
            return _ask_gemini(key, prompt, system, temperature)
        if ptype == "cohere":
            return _ask_cohere(key, prompt, system, temperature)
        if ptype == "cloudflare":
            return _ask_cloudflare(prompt, system, temperature)
        if ptype == "openrouter":
            return _ask_openai_compat(or_url, key, "meta-llama/llama-3.3-70b-instruct:free", prompt, system, temperature)
        return None

    answer = FAILOVER.execute_chain(providers, _run_provider)
    latency_ms = round((time.time() - t0) * 1000, 1)

    if answer:
        if use_cache:
            SMART_CACHE.set(prompt, answer, system, mode)
        BUS.publish("ai.response_ok", {"mode": mode, "latency_ms": latency_ms})
        return answer

    BUS.publish("ai.response_failed", {"mode": mode, "latency_ms": latency_ms})
    return "⚠ تعذر الحصول على استجابة من المحركات حالياً، يرجى إعادة المحاولة."


def ai_ask_json(prompt: str, system: str = "", mode: str = "fast"):
    raw = ai_ask(prompt, f"{system}\nأرجع النتيجة بصيغة JSON صالحة فقط بدون أي نص إضافي.", temperature=0.2, mode=mode, use_cache=False)
    clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        start, end = clean.find("{"), clean.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(clean[start:end])
    except Exception:
        pass
    return None


def send_msg(cid: str, text: str):
    if not GREEN_ID or not GREEN_TOKEN or not cid or not text:
        print(f"[MSG -> {cid}]: {text[:120]}", flush=True)
        return
    url = f"{GREEN_BASE}{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
    try:
        r = SESSION.post(url, json={"chatId": cid, "message": text}, timeout=15)
        print(f"OUT [{r.status_code}] -> {cid}: {r.text[:100]}", flush=True)
        BUS.publish("channel.whatsapp_sent", {"cid": cid, "chars": len(text)})
    except Exception as exc:
        print(f"SendMsg Err: {exc}", flush=True)


def send_file(cid: str, file_path: str, file_name: str, mime_type: str = "", caption: str = ""):
    if not GREEN_ID or not GREEN_TOKEN or not cid or not os.path.exists(file_path):
        return
    url = f"{GREEN_BASE}{GREEN_ID}/sendFileByUpload/{GREEN_TOKEN}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, mime_type or "application/octet-stream")}
            data = {"chatId": cid, "fileName": file_name, "caption": caption}
            r = SESSION.post(url, data=data, files=files, timeout=45)
        print(f"OUT_FILE [{r.status_code}] -> {cid}: {r.text[:100]}", flush=True)
        BUS.publish("channel.whatsapp_file_sent", {"cid": cid, "file": file_name})
    except Exception as exc:
        print(f"SendFile Err: {exc}", flush=True)

import os
import json
import time
import requests
from core.config import (
    SB_URL, SB_KEY, GREEN_ID, GREEN_TOKEN, GREEN_BASE,
    GEM_KEYS, GROQ_KEYS, SAMBA_KEYS, COHERE_KEYS, OR_KEYS,
    CF_ACCOUNT, CF_TOKEN, URLS, rotated_keys
)
from core.failover_cache import SMART_CACHE, FAILOVER
from core.event_bus import BUS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Albaraa-AI-OS/3.0"})

# متغيرات توافقية لباقي وحدات النظام
GEMINI_BASE_URL = URLS["gemini"]
GEM_KEY = GEM_KEYS[0] if GEM_KEYS else ""
_rotated = rotated_keys


def sb(method: str, table: str, data=None, q: str = ""):
    """التعامل المباشر مع جداول Supabase."""
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


def _build_messages(prompt: str, system: str) -> list[dict]:
    msgs = [{"role": "system", "content": system}] if system else []
    msgs.append({"role": "user", "content": prompt})
    return msgs


def _ask_openai_compat(base_url: str, key: str, model: str, prompt: str, system: str, temp: float):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": _build_messages(prompt, system), "temperature": temp, "max_tokens": 2048}
    r = SESSION.post(base_url, headers=headers, json=payload, timeout=22)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"].strip()
    return None


def _ask_gemini(key: str, prompt: str, system: str, temp: float):
    full_text = f"{system}\n\n{prompt}".strip() if system else prompt
    payload = {
        "contents": [{"parts": [{"text": full_text}]}],
        "generationConfig": {"temperature": temp, "maxOutputTokens": 2048},
    }
    for model in ("gemini-2.0-flash", "gemini-1.5-flash"):
        url = f"{URLS['gemini']}{model}:generateContent?key={key}"
        r = SESSION.post(url, json=payload, timeout=22)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return None


def _ask_cohere(key: str, prompt: str, system: str, temp: float):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": "command-r-plus-08-2024", "messages": _build_messages(prompt, system), "temperature": temp}
    r = SESSION.post(URLS["cohere"], headers=headers, json=payload, timeout=22)
    if r.status_code == 200:
        return r.json()["message"]["content"][0]["text"].strip()
    return None
    def _ask_cloudflare(prompt: str, system: str, temp: float):
    if not CF_ACCOUNT or not CF_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    r = SESSION.post(URLS["cloudflare"], headers=headers, json={"messages": _build_messages(prompt, system), "temperature": temp}, timeout=22)
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

    pools = {
        "gemini": rotated_keys(GEM_KEYS),
        "cohere": rotated_keys(COHERE_KEYS),
        "groq": rotated_keys(GROQ_KEYS),
        "samba": rotated_keys(SAMBA_KEYS),
        "openrouter": rotated_keys(OR_KEYS),
        "cloudflare": ["cf"] if (CF_ACCOUNT and CF_TOKEN) else [],
    }
    order = {
        "arabic": ["gemini", "cohere", "groq", "samba", "cloudflare", "openrouter"],
        "fast": ["groq", "samba", "cloudflare", "gemini", "openrouter"],
    }.get(mode, ["groq", "gemini", "samba", "cohere", "cloudflare", "openrouter"])

    providers = [(p, k) for p in order for k in pools[p]]

    def _run_provider(prov):
        ptype, key = prov
        if ptype == "groq":
            return _ask_openai_compat(URLS["groq_chat"], key, "llama-3.3-70b-versatile", prompt, system, temperature)
        if ptype == "samba":
            return _ask_openai_compat(URLS["samba"], key, "Meta-Llama-3.3-70B-Instruct", prompt, system, temperature)
        if ptype == "gemini":
            return _ask_gemini(key, prompt, system, temperature)
        if ptype == "cohere":
            return _ask_cohere(key, prompt, system, temperature)
        if ptype == "cloudflare":
            return _ask_cloudflare(prompt, system, temperature)
        if ptype == "openrouter":
            return _ask_openai_compat(URLS["openrouter"], key, "meta-llama/llama-3.3-70b-instruct:free", prompt, system, temperature)
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
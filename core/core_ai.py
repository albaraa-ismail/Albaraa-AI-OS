import os
import json
import time
from typing import Any, Callable, Optional
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

GEMINI_BASE_URL = URLS["gemini"]
GEM_KEY = GEM_KEYS[0] if GEM_KEYS else ""
_rotated = rotated_keys

DEFAULT_TIMEOUT = 45
MODE_ROUTING: dict[str, list[str]] = {
    "arabic": ["gemini", "groq", "cohere", "openrouter", "cloudflare", "samba"],
    "fast": ["groq", "gemini", "openrouter", "cohere", "cloudflare", "samba"],
    "general": ["groq", "gemini", "cohere", "openrouter", "cloudflare", "samba"],
}

OPENAI_COMPAT_MODELS: dict[str, tuple[str, str]] = {
    "groq": (URLS["groq_chat"], "llama-3.1-8b-instant"),
    "samba": (URLS["samba"], "Meta-Llama-3.3-70B-Instruct"),
    "openrouter": (URLS["openrouter"], "openrouter/free"),
}


def sb(method: str, table: str, data: Any = None, q: str = "") -> Any:
    method_upper = method.upper()
    fallback = [] if method_upper == "GET" else None

    if not SB_URL or not SB_KEY:
        return fallback

    url = f"{SB_URL}/rest/v1/{table}{q}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        res = SESSION.request(method_upper, url, headers=headers, json=data, timeout=15)
        if res.status_code in (200, 201):
            return res.json()
    except Exception as exc:
        print(f"SB Err [{table}]: {exc}", flush=True)

    return fallback


def _build_messages(prompt: str, system: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})
    return messages


def _ask_openai_compat(provider: str, key: str, prompt: str, system: str, temp: float) -> Optional[str]:
    base_url, model = OPENAI_COMPAT_MODELS[provider]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": _build_messages(prompt, system),
        "temperature": temp,
        "max_tokens": 2048,
    }
    res = SESSION.post(base_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"].strip()
    print(f"API Err [{provider}]: {res.status_code} - {res.text[:120]}", flush=True)
    return None


def _ask_gemini(key: str, prompt: str, system: str, temp: float) -> Optional[str]:
    full_text = f"{system}\n\n{prompt}".strip() if system else prompt
    payload = {
        "contents": [{"parts": [{"text": full_text}]}],
        "generationConfig": {"temperature": temp, "maxOutputTokens": 2048},
    }
    for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        url = f"{URLS['gemini']}{model}:generateContent?key={key}"
        res = SESSION.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        if res.status_code == 200:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"API Err [gemini:{model}]: {res.status_code} - {res.text[:120]}", flush=True)
    return None


def _ask_cohere(key: str, prompt: str, system: str, temp: float) -> Optional[str]:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "command-r-plus-08-2024",
        "messages": _build_messages(prompt, system),
        "temperature": temp,
        "max_tokens": 2048,
    }
    res = SESSION.post(URLS["cohere"], headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    if res.status_code == 200:
        return res.json()["message"]["content"][0]["text"].strip()
    print(f"API Err [cohere]: {res.status_code} - {res.text[:120]}", flush=True)
    return None
def _ask_cloudflare(prompt: str, system: str, temp: float) -> Optional[str]:
    if not CF_ACCOUNT or not CF_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    payload = {"messages": _build_messages(prompt, system), "temperature": temp}
    res = SESSION.post(URLS["cloudflare"], headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    if res.status_code == 200:
        return res.json().get("result", {}).get("response", "").strip()
    print(f"API Err [cloudflare]: {res.status_code} - {res.text[:120]}", flush=True)
    return None


def ai_ask(
    prompt: str,
    system: str = "",
    temperature: float = 0.4,
    mode: str = "general",
    use_cache: bool = True,
) -> str:
    t0 = time.time()

    if use_cache:
        cached = SMART_CACHE.get(prompt, system, mode)
        if cached:
            latency_ms = round((time.time() - t0) * 1000, 1)
            BUS.publish("ai.cache_hit", {"mode": mode, "latency_ms": latency_ms})
            return cached

    pools: dict[str, list[str]] = {
        "gemini": rotated_keys(GEM_KEYS),
        "cohere": rotated_keys(COHERE_KEYS),
        "groq": rotated_keys(GROQ_KEYS),
        "samba": rotated_keys(SAMBA_KEYS),
        "openrouter": rotated_keys(OR_KEYS),
        "cloudflare": ["cf"] if (CF_ACCOUNT and CF_TOKEN) else [],
    }

    order = MODE_ROUTING.get(mode, MODE_ROUTING["general"])
    providers = [(provider, key) for provider in order for key in pools[provider]]

    handlers: dict[str, Callable[[str], Optional[str]]] = {
        "groq": lambda k: _ask_openai_compat("groq", k, prompt, system, temperature),
        "samba": lambda k: _ask_openai_compat("samba", k, prompt, system, temperature),
        "openrouter": lambda k: _ask_openai_compat("openrouter", k, prompt, system, temperature),
        "gemini": lambda k: _ask_gemini(k, prompt, system, temperature),
        "cohere": lambda k: _ask_cohere(k, prompt, system, temperature),
        "cloudflare": lambda _: _ask_cloudflare(prompt, system, temperature),
    }

    answer = FAILOVER.execute_chain(providers, lambda prov: handlers[prov](prov))
    latency_ms = round((time.time() - t0) * 1000, 1)

    if answer:
        if use_cache:
            SMART_CACHE.set(prompt, answer, system, mode)
        BUS.publish("ai.response_ok", {"mode": mode, "latency_ms": latency_ms})
        return answer

    BUS.publish("ai.response_failed", {"mode": mode, "latency_ms": latency_ms})
    return "⚠ تعذر الحصول على استجابة من المحركات حالياً، يرجى إعادة المحاولة."


def ai_ask_json(prompt: str, system: str = "", mode: str = "fast") -> Optional[dict[str, Any]]:
    json_system = f"{system}\nأرجع النتيجة بصيغة JSON صالحة فقط بدون أي نص إضافي.".strip()
    raw = ai_ask(prompt, json_system, temperature=0.2, mode=mode, use_cache=False)
    clean = raw.replace("```json", "").replace("```", "").strip()

    try:
        start, end = clean.find("{"), clean.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(clean[start:end])
    except json.JSONDecodeError:
        pass
    return None


def send_msg(cid: str, text: str) -> None:
    if not GREEN_ID or not GREEN_TOKEN or not cid or not text:
        print(f"[MSG -> {cid}]: {text[:120]}", flush=True)
        return

    url = f"{GREEN_BASE}{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
    try:
        res = SESSION.post(url, json={"chatId": cid, "message": text}, timeout=15)
        print(f"OUT [{res.status_code}] -> {cid}: {res.text[:100]}", flush=True)
        BUS.publish("channel.whatsapp_sent", {"cid": cid, "chars": len(text)})
    except Exception as exc:
        print(f"SendMsg Err: {exc}", flush=True)


def send_file(cid: str, file_path: str, file_name: str, mime_type: str = "", caption: str = "") -> None:
    if not GREEN_ID or not GREEN_TOKEN or not cid or not os.path.exists(file_path):
        return

    url = f"{GREEN_BASE}{GREEN_ID}/sendFileByUpload/{GREEN_TOKEN}"
    try:
        with open(file_path, "rb") as file_obj:
            files = {"file": (file_name, file_obj, mime_type or "application/octet-stream")}
            data = {"chatId": cid, "fileName": file_name, "caption": caption}
            res = SESSION.post(url, data=data, files=files, timeout=45)
        print(f"OUT_FILE [{res.status_code}] -> {cid}: {res.text[:100]}", flush=True)
        BUS.publish("channel.whatsapp_file_sent", {"cid": cid, "file": file_name})
    except Exception as exc:
        print(f"SendFile Err: {exc}", flush=True)

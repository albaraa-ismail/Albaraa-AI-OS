import re
import json
import base64
from typing import Any, Optional
import requests

from core.config import (
    SB_URL, SB_KEY, GREEN_ID, GREEN_TOKEN, GREEN_BASE,
    GEM_KEYS, GROQ_KEYS, SAMBA_KEYS, COHERE_KEYS, OR_KEYS,
    CF_ACCOUNT, CF_TOKEN, URLS, rotated_keys
)
from core.failover_cache import SMART_CACHE, FAILOVER
from core.event_bus import BUS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Albaraa-AI-OS/3.5"})
DEFAULT_TIMEOUT = 45

GEMINI_BASE_URL = URLS["gemini"]
GEM_KEY = GEM_KEYS[0] if GEM_KEYS else ""
_rotated = rotated_keys

MODE_ROUTING: dict[str, list[str]] = {
    "arabic": ["gemini", "groq", "cohere", "openrouter", "cloudflare"],
    "fast": ["groq", "gemini", "cloudflare", "openrouter"],
    "general": ["gemini", "groq", "cohere", "openrouter", "cloudflare"],
    "reasoning": ["gemini", "groq", "cohere", "openrouter"],
    "coding": ["gemini", "groq", "openrouter", "cloudflare"],
    "office": ["gemini", "groq", "cohere", "openrouter"],
}

GEMINI_MODELS = ("gemini-2.5-pro", "gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-flash-latest")

OPENAI_COMPAT: dict[str, tuple[str, str]] = {
    "groq": (URLS["groq_chat"], "llama-3.3-70b-versatile"),
    "samba": (URLS.get("samba", "https://sambanova.ai"), "Meta-Llama-3.3-70B-Instruct"),
    "openrouter": (URLS["openrouter"], "openrouter/free"),
}

KEY_POOLS: dict[str, list[str]] = {
    "gemini": GEM_KEYS,
    "groq": GROQ_KEYS,
    "samba": SAMBA_KEYS,
    "cohere": COHERE_KEYS,
    "openrouter": OR_KEYS,
}


def sb(method: str, table: str, data: Any = None, q: str = "") -> Any:
    method_upper = method.upper()
    fallback = [] if method_upper == "GET" else None
    if not SB_URL or not SB_KEY:
        return fallback

    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        res = SESSION.request(method_upper, f"{SB_URL}/rest/v1/{table}{q}", headers=headers, json=data, timeout=15)
        if res.status_code in (200, 201):
            return res.json()
    except Exception as exc:
        print(f"SB Err [{table}]: {exc}", flush=True)
    return fallback


def send_msg(chat_id: str, text: str) -> Optional[dict[str, Any]]:
    if not GREEN_ID or not GREEN_TOKEN or not chat_id:
        return None
    target = chat_id if "@" in chat_id else f"{chat_id}@c.us"
    base = GREEN_BASE.rstrip("/")
    if "waInstance" in base:
        url = f"{base}/sendMessage/{GREEN_TOKEN}"
    else:
        url = f"{base}/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
    try:
        res = SESSION.post(url, json={"chatId": target, "message": text}, timeout=15)
        if res.status_code == 200:
            data = res.json()
            print(f"OUT -> {target}: {json.dumps(data)}", flush=True)
            return data
        print(f"WA Err [{res.status_code}]: {res.text[:120]}", flush=True)
    except Exception as exc:
        print(f"WA Conn Err: {exc}", flush=True)
    return None


def _messages(prompt: str, system: str) -> list[dict[str, str]]:
    return ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]


def _post(url: str, payload: dict[str, Any], headers: Optional[dict[str, str]] = None, tag: str = "") -> Optional[dict[str, Any]]:
    try:
        res = SESSION.post(url, headers=headers or {"Content-Type": "application/json"}, json=payload, timeout=DEFAULT_TIMEOUT)
        if res.status_code == 200:
            return res.json()
        print(f"API Err [{tag}]: {res.status_code} - {res.text[:120]}", flush=True)
    except Exception as exc:
        print(f"Conn Err [{tag}]: {exc}", flush=True)
    return None


def _ask_openai_compat(provider: str, key: str, prompt: str, system: str, temp: float, max_tokens: int) -> Optional[str]:
    url, model = OPENAI_COMPAT[provider]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": _messages(prompt, system), "temperature": temp, "max_tokens": max_tokens}
    data = _post(url, payload, headers, provider)
    try:
        content = data["choices"][0]["message"]["content"]
        return content.strip() if isinstance(content, str) and content.strip() else None
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def _ask_gemini(key: str, prompt: str, system: str, temp: float, max_tokens: int) -> Optional[str]:
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temp, "maxOutputTokens": max_tokens},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    for model in GEMINI_MODELS:
        data = _post(f"{URLS['gemini']}{model}:generateContent?key={key}", payload, tag=f"gemini:{model}")
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            if isinstance(text, str) and text.strip():
                return text.strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            continue
    return None
def _ask_cohere(key: str, prompt: str, system: str, temp: float, max_tokens: int) -> Optional[str]:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": "command-a-03-2025", "messages": _messages(prompt, system), "temperature": temp, "max_tokens": max_tokens}
    data = _post(URLS["cohere"], payload, headers, "cohere")
    try:
        content = data["message"]["content"]
        if isinstance(content, list) and content:
            text = content.get("text", "")
        elif isinstance(content, dict):
            text = content.get("text", "")
        else:
            text = ""
        return text.strip() if isinstance(text, str) and text.strip() else None
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def _ask_cloudflare(prompt: str, system: str, temp: float) -> Optional[str]:
    if not CF_ACCOUNT or not CF_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    data = _post(URLS["cloudflare"], {"messages": _messages(prompt, system), "temperature": temp}, headers, "cloudflare")
    try:
        resp = (data or {}).get("result", {}).get("response")
        return resp.strip() if isinstance(resp, str) and resp.strip() else None
    except AttributeError:
        return None


def _call_provider(provider: str, prompt: str, system: str, temp: float, max_tokens: int) -> Optional[str]:
    if provider == "cloudflare":
        return _ask_cloudflare(prompt, system, temp)

    keys = _rotated(KEY_POOLS.get(provider, []))
    for key in keys:
        if provider in OPENAI_COMPAT:
            res = _ask_openai_compat(provider, key, prompt, system, temp, max_tokens)
        elif provider == "gemini":
            res = _ask_gemini(key, prompt, system, temp, max_tokens)
        elif provider == "cohere":
            res = _ask_cohere(key, prompt, system, temp, max_tokens)
        else:
            res = None
        if res:
            return res
    return None


def ai_ask(
    prompt: str,
    system: str = "",
    temperature: float = 0.4,
    mode: str = "general",
    max_tokens: int = 2048,
    use_cache: bool = True,
) -> str:
    if use_cache:
        cached = SMART_CACHE.get(prompt, system, mode)
        if cached:
            return cached

    providers = MODE_ROUTING.get(mode, MODE_ROUTING["general"])
    for provider in providers:
        if hasattr(FAILOVER, "is_available") and not FAILOVER.is_available(provider):
            continue

        reply = _call_provider(provider, prompt, system, temperature, max_tokens)
        if reply:
            if hasattr(FAILOVER, "record_success"):
                FAILOVER.record_success(provider)
            if use_cache:
                SMART_CACHE.set(prompt, system, mode, reply)
            BUS.emit("ai_response", {"provider": provider, "mode": mode})
            return reply

        if hasattr(FAILOVER, "record_failure"):
            FAILOVER.record_failure(provider)

    return "عذراً، جميع محركات الذكاء الاصطناعي مشغولة حالياً. يرجى المحاولة بعد قليل."


def ai_vision(image_bytes: bytes, mime_type: str, prompt: str, system: str = "") -> Optional[str]:
    if not GEM_KEYS:
        return None
    b64_data = base64.b64encode(image_bytes).decode("utf-8")
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": b64_data}}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    for key in _rotated(GEM_KEYS):
        for model in GEMINI_MODELS:
            data = _post(f"{URLS['gemini']}{model}:generateContent?key={key}", payload, tag=f"vision:{model}")
            try:
                text = data["candidates"]["content"]["parts"]["text"]
                if isinstance(text, str) and text.strip():
                    return text.strip()
            except (KeyError, IndexError, TypeError, AttributeError):
                continue
    return None


def ai_generate_image(prompt: str) -> Optional[bytes]:
    translated = ai_ask(
        f"Convert this description into a clean, professional English image prompt (max 35 words, no extra text): {prompt}",
        mode="fast",
        use_cache=False,
    )
    en_prompt = prompt if "عذراً، جميع محركات" in translated else translated

    if CF_ACCOUNT and CF_TOKEN:
        cf_base = "".join(["https://", "api.", "cloudflare.com", "/client/v4/accounts"])
        url = f"{cf_base}/{CF_ACCOUNT}/ai/run/@cf/black-forest-labs/flux-1-schnell"
        try:
            res = SESSION.post(url, headers={"Authorization": f"Bearer {CF_TOKEN}"}, json={"prompt": en_prompt}, timeout=45)
            if res.status_code == 200 and res.content:
                return res.content
        except Exception as exc:
            print(f"CF Image Err: {exc}", flush=True)

    try:
        encoded = requests.utils.quote(en_prompt)
        fallback_base = "".join(["https://", "image.", "pollinations.ai", "/prompt/"])
        res = SESSION.get(f"{fallback_base}{encoded}?width=1024&height=1024&nologo=true", timeout=45)
        if res.status_code == 200 and res.content:
            return res.content
    except Exception as exc:
        print(f"Fallback Image Err: {exc}", flush=True)
    return None


def ai_ask_json(prompt: str, system: str = "", mode: str = "fast") -> dict[str, Any]:
    strict_system = f"{system}\nأجب بصيغة JSON صالحة فقط بدون أي نص إضافي أو علامات Markdown.".strip()
    raw = ai_ask(prompt, system=strict_system, temperature=0.1, mode=mode, use_cache=False)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    cleaned = match.group(0) if match else raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {"raw_response": raw, "parse_error": True}


def check_providers_health() -> dict[str, bool]:
    return {
        "gemini": bool(GEM_KEYS),
        "groq": bool(GROQ_KEYS),
        "samba": bool(SAMBA_KEYS),
        "cohere": bool(COHERE_KEYS),
        "openrouter": bool(OR_KEYS),
        "cloudflare": bool(CF_ACCOUNT and CF_TOKEN),
        "supabase": bool(SB_URL and SB_KEY),
    }


def inspect_api_keys_report() -> str:
    lines = ["🔑 *تقرير فحص المفاتيح والأرصدة الحية:*\n"]

    if OR_KEYS:
        lines.append(f"🌐 *OpenRouter* (عدد المفاتيح: {len(OR_KEYS)}):")
        for idx, k in enumerate(OR_KEYS, 1):
            masked = f"{k[:8]}...{k[-4:]}" if len(k) > 12 else "***"
            try:
                r = SESSION.get("https://openrouter.ai", headers={"Authorization": f"Bearer {k}"}, timeout=8)
                if r.status_code == 200:
                    info = r.json().get("data", {})
                    limit = info.get("limit")
                    usage = round(float(info.get("usage", 0)), 4)
                    bal = f"متبقي: ${round(limit - usage, 3)}" if limit is not None else f"مستهلك: ${usage} (مجاني/غير محدود)"
                    lines.append(f"  • مفتاح {idx} (`{masked}`): ✅ نشط ({bal})")
                else:
                    lines.append(f"  • مفتاح {idx} (`{masked}`): ❌ خطأ ({r.status_code})")
            except Exception:
                lines.append(f"  • مفتاح {idx} (`{masked}`): ⚠️ تعذر الاتصال")
    else:
        lines.append("🌐 *OpenRouter*: ⚪ لا توجد مفاتيح مضافة")

    if GEM_KEYS:
        lines.append(f"\n✨ *Google Gemini* (عدد المفاتيح: {len(GEM_KEYS)}):")
        for idx, k in enumerate(GEM_KEYS, 1):
            masked = f"{k[:8]}...{k[-4:]}" if len(k) > 12 else "***"
            try:
                r = SESSION.get(f"{URLS['gemini']}?key={k}", timeout=8)
                status = "✅ نشط ومتاح" if r.status_code == 200 else f"❌ غير صالح/محظور ({r.status_code})"
                lines.append(f"  • مفتاح {idx} (`{masked}`): {status}")
            except Exception:
                lines.append(f"  • مفتاح {idx} (`{masked}`): ⚠️ تعذر الاتصال")
    else:
        lines.append("\n✨ *Google Gemini*: ⚪ لا توجد مفاتيح مضافة")

    if GROQ_KEYS:
        lines.append(f"\n⚡ *Groq* (عدد المفاتيح: {len(GROQ_KEYS)}):")
        for idx, k in enumerate(GROQ_KEYS, 1):
            masked = f"{k[:8]}...{k[-4:]}" if len(k) > 12 else "***"
            try:
                r = SESSION.get("https://groq.com", headers={"Authorization": f"Bearer {k}"}, timeout=8)
                status = "✅ نشط ومتاح" if r.status_code == 200 else f"❌ منتهي/خطأ ({r.status_code})"
                lines.append(f"  • مفتاح {idx} (`{masked}`): {status}")
            except Exception:
                lines.append(f"  • مفتاح {idx} (`{masked}`): ⚠️ تعذر الاتصال")
    else:
        lines.append("\n⚡ *Groq*: ⚪ لا توجد مفاتيح مضافة")

    lines.append(f"\n🧠 *Cohere*: {len(COHERE_KEYS)} مفاتيح مسجلة")
    lines.append(f"🚀 *SambaNova*: {len(SAMBA_KEYS)} مفاتيح مسجلة")
    lines.append(f"☁️ *Cloudflare AI*: {'✅ مفعّل' if (CF_ACCOUNT and CF_TOKEN) else '⚪ غير مفعّل'}")

    return "\n".join(lines)

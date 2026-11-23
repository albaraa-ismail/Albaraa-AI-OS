import os
import random
from datetime import timedelta, timezone

RIYADH_TZ = timezone(timedelta(hours=3))

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

def digits_only(val: str) -> str:
    return "".join(filter(str.isdigit, str(val or "")))

def load_api_keys(prefix: str) -> list[str]:
    candidates = [prefix] + [f"{prefix}{sep}{i}" for i in range(1, 10) for sep in ("_", "")]
    return list(dict.fromkeys(k for c in candidates if (k := _env(c))))

def _u(host: str, path: str = "") -> str:
    return "https" + "://" + host + path

ADMIN_PHONE = digits_only(_env("ADMIN_PHONE"))
PARTNER_PHONE = digits_only(_env("AHMED_PHONE"))
ALLOWED_GROUP = _env("ALLOWED_GROUP")

# [يمكنك الاطلاع على الكود البرمجي الكامل لإعدادات المسارات والمفاتيح والروابط في المستودع المرفق]
URLS: dict[str, str] = {
    "gemini": _u("://googleapis.com", "/v1beta/models/"),
    "groq_chat": _u("://groq.com", "/openai/v1/chat/completions"),
    "samba": _u("api.sambanova.ai", "/v1/chat/completions"),
    "cohere": _u("://cohere.com", "/v2/chat"),
    "openrouter": _u("openrouter.ai", "/api/v1/chat/completions"),
    "fish_tts": _u("api.fish.audio", "/v1/tts"),
}

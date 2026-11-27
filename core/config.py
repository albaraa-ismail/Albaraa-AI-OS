import os
import random
from datetime import timedelta, timezone

RIYADH_TZ = timezone(timedelta(hours=3))


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def digits_only(val: str) -> str:
    return "".join(filter(str.isdigit, str(val or "")))


def load_api_keys(prefix: str) -> list[str]:
    short = prefix.replace("_API_KEY", "_KEY")
    base_names = [prefix, f"{prefix}S", short, f"{short}S"]
    candidates = list(base_names)
    for base in base_names:
        candidates.extend([f"{base}{sep}{i}" for i in range(1, 20) for sep in ("_", "")])

    found: list[str] = []
    for c in candidates:
        raw = _env(c)
        if raw:
            for item in raw.replace("\n", ",").split(","):
                clean_k = item.strip()
                if clean_k and clean_k not in found:
                    found.append(clean_k)
    return found


def rotated_keys(keys: list[str]) -> list[str]:
    if len(keys) <= 1:
        return list(keys)
    idx = random.randrange(len(keys))
    return keys[idx:] + keys[:idx]


def _build_url(*parts: str) -> str:
    return "https" + ":" + "//" + "".join(parts)


ADMIN_PHONE = digits_only(_env("ADMIN_PHONE"))
PARTNER_PHONE = digits_only(_env("AHMED_PHONE"))
ALLOWED_GROUP = _env("ALLOWED_GROUP")

RENDER_URL = _env("RENDER_EXTERNAL_URL").rstrip("/")
GITHUB_TOKEN = _env("GITHUB_TOKEN")
GITHUB_REPO = _env("GITHUB_REPO", "albaraa-ismail/Albaraa-AI-OS")
GITHUB_API = _build_url("api.", "github.com")

SB_URL = _env("SUPABASE_URL").rstrip("/")
SB_KEY = _env("SUPABASE_KEY")

GREEN_ID = _env("GREEN_API_ID") or _env("GREEN_ID_INSTANCE")
GREEN_TOKEN = _env("GREEN_API_TOKEN")
_raw_green = _env("GREEN_API_URL").rstrip("/")
GREEN_BASE = _raw_green.removesuffix("/waInstance") if _raw_green else _build_url("api.", "green-api.com")

GEM_KEYS = load_api_keys("GEMINI_API_KEY")
GROQ_KEYS = load_api_keys("GROQ_API_KEY")
SAMBA_KEYS = load_api_keys("SAMBANOVA_API_KEY")
COHERE_KEYS = load_api_keys("COHERE_API_KEY")
OR_KEYS = load_api_keys("OPENROUTER_API_KEY")

CF_ACCOUNT = _env("CF_ACCOUNT_ID") or _env("CLOUDFLARE_ACCOUNT_ID")
CF_TOKEN = _env("CF_API_KEY") or _env("CLOUDFLARE_API_TOKEN")

FISH_KEY = _env("FISH_API_KEY")
MY_VOICE_ID = _env("MY_VOICE_ID")

URLS: dict[str, str] = {
    "gemini": _build_url("generativelanguage.", "googleapis.com", "/v1beta/models/"),
    "groq_chat": _build_url("api.", "groq.com", "/openai/v1/chat/completions"),
    "groq_audio": _build_url("api.", "groq.com", "/openai/v1/audio/transcriptions"),
    "samba": _build_url("api.", "sambanova.ai", "/v1/chat/completions"),
    "cohere": _build_url("api.", "cohere.com", "/v2/chat"),
    "openrouter": _build_url("openrouter.ai", "/api/v1/chat/completions"),
    "cloudflare": (
        _build_url("api.", "cloudflare.com", f"/client/v4/accounts/{CF_ACCOUNT}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast")
        if CF_ACCOUNT else ""
    ),
    "fish_tts": _build_url("api.", "fish.audio", "/v1/tts"),
}

import os
import random
from datetime import timedelta, timezone

# توقيت الرياض الموحد للنظام
RIYADH_TZ = timezone(timedelta(hours=3))


def _env(key: str, default: str = "") -> str:
    """قراءة وتنظيف متغير البيئة بأمان."""
    return os.environ.get(key, default).strip()


def digits_only(val: str) -> str:
    """استخراج الأرقام فقط من النصوص وأرقام الجوال."""
    return "".join(filter(str.isdigit, str(val or "")))


def load_api_keys(prefix: str) -> list[str]:
    """جلب مفاتيح API الأساسية والاحتياطية بدون تكرار."""
    keys: list[str] = []
    if base := _env(prefix):
        keys.append(base)
    for i in range(1, 10):
        for fmt in (f"{prefix}_{i}", f"{prefix}{i}"):
            if (key := _env(fmt)) and key not in keys:
                keys.append(key)
    return keys


def rotated_keys(keys: list[str]) -> list[str]:
    """تدوير المفاتيح عشوائياً لتوزيع الضغط."""
    if len(keys) <= 1:
        return list(keys)
    idx = random.randint(0, len(keys) - 1)
    return keys[idx:] + keys[:idx]


# --- أرقام الإدارة والصلاحيات ---
ADMIN_PHONE = digits_only(_env("ADMIN_PHONE"))
PARTNER_PHONE = digits_only(_env("AHMED_PHONE"))
ALLOWED_GROUP = _env("ALLOWED_GROUP")

# --- روابط وإعدادات السحابة والخدمات ---
RENDER_URL = _env("RENDER_EXTERNAL_URL").rstrip("/")
GITHUB_TOKEN = _env("GITHUB_TOKEN")
GITHUB_REPO = _env("GITHUB_REPO", "albaraa-ismail/Albaraa-AI-OS")
GITHUB_API = "https://api.github.com"

# --- قاعدة البيانات Supabase ---
SB_URL = _env("SUPABASE_URL").rstrip("/")
SB_KEY = _env("SUPABASE_KEY")

# --- بوابة واتساب Green API ---
GREEN_ID = _env("GREEN_API_ID") or _env("GREEN_ID_INSTANCE")
GREEN_TOKEN = _env("GREEN_API_TOKEN")
_raw_green = _env("GREEN_API_URL").rstrip("/")
GREEN_BASE = (
    (_raw_green if _raw_green.endswith("waInstance") else f"{_raw_green}/waInstance")
    if _raw_green
    else "https://green-api.com"
)

# --- مفاتيح وروابط نماذج الذكاء الاصطناعي ---
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
    "gemini": "https://googleapis.com",
    "groq_chat": "https://groq.com",
    "groq_audio": "https://groq.com",
    "samba": "https://sambanova.ai",
    "cohere": "https://cohere.com",
    "openrouter": "https://openrouter.ai",
    "cloudflare": f"https://cloudflare.com{CF_ACCOUNT}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "fish_tts": "https://fish.audio",
}
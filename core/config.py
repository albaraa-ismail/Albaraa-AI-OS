import os
import random
from datetime import timezone, timedelta

# توقيت الرياض الموحد للنظام
RIYADH_TZ = timezone(timedelta(hours=3))


def digits_only(val: str) -> str:
    """استخراج الأرقام فقط من النصوص وأرقام الجوال."""
    return "".join(filter(str.isdigit, str(val or "")))


def load_api_keys(prefix: str) -> list[str]:
    """جلب مفاتيح API الأساسية والاحتياطية بدون تكرار."""
    keys = []
    base = os.environ.get(prefix, "").strip()
    if base:
        keys.append(base)
    for i in range(1, 10):
        for fmt in (f"{prefix}_{i}", f"{prefix}{i}"):
            k = os.environ.get(fmt, "").strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def rotated_keys(keys: list[str]) -> list[str]:
    """تدوير المفاتيح عشوائياً لتوزيع الضغط."""
    if len(keys) <= 1:
        return list(keys)
    idx = random.randint(0, len(keys) - 1)
    return keys[idx:] + keys[:idx]


# --- أرقام الإدارة والصلاحيات ---
ADMIN_PHONE = digits_only(os.environ.get("ADMIN_PHONE", ""))
PARTNER_PHONE = digits_only(os.environ.get("AHMED_PHONE", ""))
ALLOWED_GROUP = os.environ.get("ALLOWED_GROUP", "").strip()

# --- روابط وإعدادات السحابة والخدمات ---
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "albaraa-ismail/Albaraa-AI-OS").strip()
GITHUB_API = "https://github.com"

# --- قاعدة البيانات Supabase ---
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

# --- بوابة واتساب Green API ---
GREEN_ID = (os.environ.get("GREEN_API_ID") or os.environ.get("GREEN_ID_INSTANCE") or "").strip()
GREEN_TOKEN = os.environ.get("GREEN_API_TOKEN", "").strip()
_raw_green = (os.environ.get("GREEN_API_URL") or "").strip().rstrip("/")
GREEN_BASE = (
    (_raw_green if _raw_green.endswith("waInstance") else f"{_raw_green}/waInstance")
    if _raw_green else "https://green-api.com"
)

# --- مفاتيح وروابط نماذج الذكاء الاصطناعي ---
GEM_KEYS = load_api_keys("GEMINI_API_KEY")
GROQ_KEYS = load_api_keys("GROQ_API_KEY")
SAMBA_KEYS = load_api_keys("SAMBANOVA_API_KEY")
COHERE_KEYS = load_api_keys("COHERE_API_KEY")
OR_KEYS = load_api_keys("OPENROUTER_API_KEY")

CF_ACCOUNT = (os.environ.get("CF_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
CF_TOKEN = (os.environ.get("CF_API_KEY") or os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()

FISH_KEY = os.environ.get("FISH_API_KEY", "").strip()
MY_VOICE_ID = os.environ.get("MY_VOICE_ID", "").strip()

URLS = {
    "gemini": "https://googleapis.com",
    "groq_chat": "https://groq.com",
    "groq_audio": "https://groq.com",
    "samba": "https://sambanova.ai",
    "cohere": "https://cohere.com",
    "openrouter": "https://openrouter.ai",
    "cloudflare": f"https://cloudflare.com{CF_ACCOUNT}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "fish_tts": "https://fish.audio",
}
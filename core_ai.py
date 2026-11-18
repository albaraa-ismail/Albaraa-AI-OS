import os
import time
import logging
import requests

logger = logging.getLogger("CoreAI")

# بناء الروابط برمجيًا لحمايتها من اختصار متصفح الآيفون
DEFAULT_G_URL = "".join(["https:/", "/api.green-api.", "com"])
GROQ_API_URL = "".join(["https:/", "/api.groq.", "com/openai/v1/chat/completions"])
GEMINI_BASE_URL = "".join(["https:/", "/generativelanguage.googleapis.", "com/v1beta/models/"])
OPENROUTER_API_URL = "".join(["https:/", "/openrouter.", "ai/api/v1/chat/completions"])

# إعدادات Green-API مع رابط افتراضي ذكي
G_URL = (os.environ.get("GREEN_API_URL") or DEFAULT_G_URL).strip().rstrip("/")
G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()

# مفاتيح الذكاء الاصطناعي وقاعدة البيانات
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

SESSION = requests.Session()

def sb(method: str, table: str, payload=None, q: str = ""):
    if not SB_URL or not SB_KEY:
        return []
    url = f"{SB_URL}/rest/v1/{table}{q}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        if method.upper() == "GET":
            res = SESSION.get(url, headers=headers, timeout=8)
        else:
            res = SESSION.post(url, json=payload, headers=headers, timeout=8)
        if res.status_code in (200, 201):
            return res.json()
        logger.warning(f"Supabase [{res.status_code}]: {res.text[:150]}")
    except Exception as e:
        logger.error(f"Supabase Exception: {e}")
    return []

def ai_ask(prompt: str, system_prompt: str) -> str:
    # 1. الطبقة الأولى: Groq (فائق السرعة)
    if GROQ_KEY:
        groq_models = ["llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"]
        for model in groq_models:
            try:
                res = SESSION.post(
                    GROQ_API_URL,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.6,
                    },
                    headers={"Authorization": f"Bearer {GROQ_KEY}"},
                    timeout=12,
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
                logger.warning(f"Groq ({model}) failed [{res.status_code}]: {res.text[:120]}")
            except Exception as e:
                logger.warning(f"Groq ({model}) exception: {e}")

    # 2. الطبقة الثانية: Google Gemini
    if GEM_KEY:
        gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
        for g_model in gemini_models:
            try:
                url = f"{GEMINI_BASE_URL}{g_model}:generateContent?key={GEM_KEY}"
                res = SESSION.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}]
                    },
                    timeout=15,
                )
                if res.status_code == 200:
                    return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                logger.warning(f"Gemini ({g_model}) failed [{res.status_code}]: {res.text[:120]}")
            except Exception as e:
                logger.warning(f"Gemini ({g_model}) exception: {e}")

    # 3. الطبقة الثالثة: OpenRouter
    if OR_KEY:
        try:
            res = SESSION.post(
                OPENROUTER_API_URL,
                json={
                    "model": "openrouter/free",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                },
                headers={"Authorization": f"Bearer {OR_KEY}"},
                timeout=18,
            )
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
            logger.warning(f"OpenRouter failed [{res.status_code}]: {res.text[:120]}")
        except Exception as e:
            logger.warning(f"OpenRouter exception: {e}")

    return "⚠️ تعذر الاتصال بمحركات الذكاء الاصطناعي حاليًا، يرجى المحاولة بعد قليل."

def send_msg(chat_id: str, text: str):
    if not text or not chat_id:
        return
    if not G_ID or not G_TOK:
        logger.error("Missing GREEN_API_ID or GREEN_API_TOKEN in environment variables!")
        return

    url = f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}"
    for attempt in range(2):
        try:
            res = SESSION.post(
                url,
                json={"chatId": chat_id, "message": text},
                timeout=15,
            )
            logger.info(f"SendMsg [{res.status_code}] to {chat_id}: {res.text[:100]}")
            if res.status_code == 200:
                return
        except Exception as e:
            logger.error(f"SendMsg attempt {attempt + 1} error: {e}")
        time.sleep(1)

def send_file(chat_id: str, path: str, name: str, mime: str, caption: str):
    if not G_ID or not G_TOK:
        logger.error("Missing GREEN_API_ID or GREEN_API_TOKEN for file upload!")
        return

    url = f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}"
    try:
        with open(path, "rb") as f:
            res = SESSION.post(
                url,
                data={"chatId": chat_id, "caption": caption},
                files={"file": (name, f, mime)},
                timeout=35,
            )
            logger.info(f"SendFile [{res.status_code}] to {chat_id}: {res.text[:100]}")
    except Exception as e:
        logger.error(f"SendFile error: {e}")

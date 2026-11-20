import os
import base64
import requests
from core.core_ai import GEM_KEYS, GROQ_KEYS, GEMINI_BASE_URL, SESSION


def transcribe_voice_note(file_url: str) -> str:
    """تفريغ البصمات الصوتية من واتساب إلى نص عربي دقيق باستخدام Whisper Large V3."""
    if not file_url or not GROQ_KEYS:
        return ""
    try:
        audio_res = SESSION.get(file_url, timeout=25)
        if audio_res.status_code != 200:
            return ""
        raw_audio = audio_res.content
        for key in GROQ_KEYS:
            r = requests.post(
                "https://groq.com",
                headers={"Authorization": f"Bearer {key}"},
                files={"file": ("voice.ogg", raw_audio, "audio/ogg")},
                data={"model": "whisper-large-v3-turbo", "language": "ar"},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json().get("text", "").strip()
    except Exception as exc:
        print(f"Voice Transcribe Err: {exc}", flush=True)
    return ""


def read_media_from_url(file_url: str, mime_type: str = "image/jpeg", user_prompt: str = "") -> str:
    """قراءة وتحليل الصور أو الملفات الصوتية المرفوعة عبر الروابط المباشرة."""
    if mime_type.startswith("audio/"):
        transcript = transcribe_voice_note(file_url)
        return f"🎙 *نص البصمة الصوتية:*\n{transcript}" if transcript else "⚠ تعذر تفريغ البصمة الصوتية."

    if not file_url or not GEM_KEYS:
        return "⚠ تعذر تحليل الوسائط لعدم توفر مفتاح الرؤية."
    try:
        res = SESSION.get(file_url, timeout=25)
        if res.status_code != 200:
            return "⚠ تعذر تحميل الملف من الرابط."
        b64 = base64.b64encode(res.content).decode("utf-8")
        prompt = user_prompt or "حلل محتوى هذه الصورة بدقة واستخرج جميع النصوص والأرقام والبيانات المهمة باللغة العربية."
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ]
            }]
        }
        for key in GEM_KEYS:
            r = SESSION.post(f"{GEMINI_BASE_URL}gemini-2.0-flash:generateContent?key={key}", json=payload, timeout=35)
            if r.status_code == 200:
                return r.json()["candidates"]["content"]["parts"]["text"].strip()
    except Exception as exc:
        print(f"Media URL Read Err: {exc}", flush=True)
    return "⚠ تعذر تحليل الوسائط حالياً."

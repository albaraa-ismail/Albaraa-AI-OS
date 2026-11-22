import asyncio
import os
import re
import time
import edge_tts

from core.config import FISH_KEY, MY_VOICE_ID, URLS
from core.core_ai import SESSION, ai_ask, send_file
from multimodal.office_tools import make_pptx

VOICE_TRIGGER_RE = re.compile(r"^(?:اقرأ بصوت نسائي|اقرأ بصوت|بصمة صوتية)[:\s]*")
STICKER_TRIGGER_RE = re.compile(r"^(?:صمم ملصق|ملصق)[:\s]*")


def _cleanup_file(path: str) -> None:
    """حذف الملف المؤقت بأمان إن وُجد."""
    if os.path.exists(path):
        os.remove(path)


async def _edge_tts_saudi(text: str, out_mp3: str, female: bool = False) -> None:
    voice_name = "ar-SA-ZariyahNeural" if female else "ar-SA-HamedNeural"
    comm = edge_tts.Communicate(text, voice_name, rate="+4%")
    await comm.save(out_mp3)


def generate_saudi_voice(text: str, out_mp3: str, female: bool = False) -> str:
    """توليد صوت سعودي طبيعي عبر استنساخ الصوت أو المحرك العصبي الاحتياطي."""
    if FISH_KEY and MY_VOICE_ID and not female:
        try:
            headers = {"Authorization": f"Bearer {FISH_KEY}", "Content-Type": "application/json"}
            payload = {"text": text, "reference_id": MY_VOICE_ID, "format": "mp3", "mp3_bitrate": 128}
            res = SESSION.post(URLS["fish_tts"], json=payload, headers=headers, timeout=25)
            if res.status_code == 200 and len(res.content) > 1000:
                with open(out_mp3, "wb") as f:
                    f.write(res.content)
                return "cloned"
        except Exception as exc:
            print(f"Fish TTS fallback: {exc}", flush=True)

    asyncio.run(_edge_tts_saudi(text, out_mp3, female=female))
    return "saudi_neural"


def make_voice_note(cid: str, msg: str) -> None:
    """تحويل النص إلى رسالة صوتية وإرسالها عبر واتساب."""
    is_female = any(k in msg for k in ("نسائي", "بنت", "امرأة", "أنثوي"))
    clean = VOICE_TRIGGER_RE.sub("", msg.strip()).strip()
    if len(clean) > 500:
        clean = ai_ask(clean, "لخص النص التالي في 3 جمل عربية فصيحة مناسبة للإلقاء الصوتي الواضح:", mode="arabic")

    out_mp3 = f"/tmp/voice_{int(time.time())}.mp3"
    try:
        generate_saudi_voice(clean, out_mp3, female=is_female)
        send_file(cid, out_mp3, "Voice_Message.mp3", "audio/mpeg", "🎙 تسجيل صوتي")
    finally:
        _cleanup_file(out_mp3)


def make_sticker(cid: str, text_or_topic: str) -> None:
    """تصميم وإرسال ملصق واتساب (WebP) بالهوية البصرية."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    from PIL import Image, ImageDraw

    clean_txt = STICKER_TRIGGER_RE.sub("", text_or_topic.strip()).strip()[:30] or "تم الإنجاز"
    reshaped = get_display(arabic_reshaper.reshape(clean_txt))

    img = Image.new("RGBA", (512, 512), (11, 25, 44, 245))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 20, 492, 492], radius=60, outline=(255, 209, 102, 255), width=8)
    draw.text((256, 256), reshaped, fill=(255, 255, 255, 255), anchor="mm")

    out_webp = f"/tmp/sticker_{int(time.time())}.webp"
    try:
        img.save(out_webp, "WEBP")
        send_file(cid, out_webp, "sticker.webp", "image/webp", "")
    finally:
        _cleanup_file(out_webp)


def make_ppt(cid: str, msg: str) -> None:
    """دالة توافقية لتوليد العروض التقديمية."""
    make_pptx(cid, msg)

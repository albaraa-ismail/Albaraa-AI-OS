import os
import time
import asyncio
import edge_tts
from core.core_ai import ai_ask, send_file, SESSION
from multimodal.office_tools import make_pptx

FISH_TTS_URL = "".join(["https:/", "/api.fish.", "audio/v1/tts"])
FISH_KEY = os.environ.get("FISH_API_KEY", "").strip()
MY_VOICE_ID = os.environ.get("MY_VOICE_ID", "").strip()


async def _edge_tts_saudi(text: str, out_mp3: str, female: bool = False):
    voice_name = "ar-SA-ZariyahNeural" if female else "ar-SA-HamedNeural"
    comm = edge_tts.Communicate(text, voice_name, rate="+4%")
    await comm.save(out_mp3)


def generate_saudi_voice(text: str, out_mp3: str, female: bool = False) -> str:
    if FISH_KEY and MY_VOICE_ID and not female:
        try:
            headers = {
                "Authorization": f"Bearer {FISH_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "text": text,
                "reference_id": MY_VOICE_ID,
                "format": "mp3",
                "mp3_bitrate": 128,
            }
            res = SESSION.post(FISH_TTS_URL, json=payload, headers=headers, timeout=25)
            if res.status_code == 200 and len(res.content) > 1000:
                with open(out_mp3, "wb") as f:
                    f.write(res.content)
                return "cloned"
        except Exception as exc:
            print(f"Fish TTS fallback: {exc}", flush=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_edge_tts_saudi(text, out_mp3, female=female))
    finally:
        loop.close()
    return "saudi_neural"


def make_voice_note(cid: str, msg: str):
    is_female = any(k in msg for k in ("نسائي", "بنت", "امرأة", "أنثوي"))
    clean = msg.replace("اقرأ بصوت نسائي", "").replace("اقرأ بصوت", "").replace("بصمة صوتية", "").lstrip(": ").strip()
    if len(clean) > 500:
        clean = ai_ask(clean, "لخص النص التالي في 3 جمل عربية فصيحة مناسبة للإلقاء الصوتي الواضح:", mode="arabic")

    ts = int(time.time())
    out_mp3 = f"/tmp/voice_{ts}.mp3"
    try:
        generate_saudi_voice(clean, out_mp3, female=is_female)
        send_file(cid, out_mp3, "Voice_Message.mp3", "audio/mpeg", "🎙 تسجيل صوتي")
    finally:
        if os.path.exists(out_mp3):
            os.remove(out_mp3)


def make_sticker(cid: str, text_or_topic: str):
    from PIL import Image, ImageDraw
    import arabic_reshaper
    from bidi.algorithm import get_display

    clean_txt = text_or_topic.replace("ملصق", "").replace("صمم ملصق", "").lstrip(": ").strip()[:30] or "تم الإنجاز"
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
        if os.path.exists(out_webp):
            os.remove(out_webp)


def make_ppt(cid: str, msg: str):
    return make_pptx(cid, msg)

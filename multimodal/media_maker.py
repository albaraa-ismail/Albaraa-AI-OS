import os
import time
import asyncio
import edge_tts
from core.core_ai import ai_ask, send_file, SESSION
from multimodal.office_tools import make_pptx

FISH_TTS_URL = "https://fish.audio"
FISH_KEY = os.environ.get("FISH_API_KEY", "").strip()
MY_VOICE_ID = os.environ.get("MY_VOICE_ID", "").strip()


async def _edge_tts_saudi(text: str, out_mp3: str):
    comm = edge_tts.Communicate(text, "ar-SA-HamedNeural", rate="+4%")
    await comm.save(out_mp3)


def generate_saudi_voice(text: str, out_mp3: str) -> str:
    """توليد الصوت السعودي البشري (صوتك المستنسخ أولاً ثم بديل HamedNeural)."""
    if FISH_KEY and MY_VOICE_ID:
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
        loop.run_until_complete(_edge_tts_saudi(text, out_mp3))
    finally:
        loop.close()
    return "saudi_neural"


def make_voice_note(cid: str, msg: str):
    """إنشاء وإرسال بصمة صوتية سعودية عبر واتساب."""
    clean = msg.replace("اقرأ بصوت", "").replace("بصمة صوتية", "").strip()
    if len(clean) > 450:
        clean = ai_ask(clean, "لخص النص التالي في 3 جمل عربية فصيحة مناسبة للإلقاء الصوتي:", mode="arabic")

    ts = int(time.time())
    out_mp3 = f"/tmp/voice_{ts}.mp3"
    try:
        mode_used = generate_saudi_voice(clean, out_mp3)
        label = "🎙 بصوتك الشخصي المستنسخ" if mode_used == "cloned" else "🎙 بالصوت السعودي الذكي"
        send_file(cid, out_mp3, "Albaraa_Voice.mp3", "audio/mpeg", label)
    finally:
        if os.path.exists(out_mp3):
            os.remove(out_mp3)


def make_ppt(cid: str, msg: str):
    """واجهة توافقية تستدعي مولد العروض التقديمية الاحترافي."""
    return make_pptx(cid, msg)

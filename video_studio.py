import os
import re
import json
import time
import asyncio
import urllib.parse
import numpy as np
import edge_tts
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from core_ai import ai_ask, send_msg, send_file, SESSION

IMG_API = "".join(["https:/", "/image.pollinations.", "ai/prompt/"])
FISH_TTS_URL = "".join(["https:/", "/api.fish.", "audio/v1/tts"])
FONT_URL = "".join(["https:/", "/://github.com"])
FONT_PATH = "/tmp/Cairo.ttf"

FISH_KEY = os.environ.get("FISH_API_KEY", "").strip()
MY_VOICE_ID = os.environ.get("MY_VOICE_ID", "").strip()

def _ensure_font():
    if not os.path.exists(FONT_PATH):
        try:
            r = SESSION.get(FONT_URL, timeout=15)
            if r.status_code == 200:
                with open(FONT_PATH, "wb") as f:
                    f.write(r.content)
        except Exception:
            pass

def _shape_ar(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def _extract_json(raw: str):
    match = re.search(r"(\{.*\})", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None

async def _fallback_tts(text: str, out_mp3: str):
    communicate = edge_tts.Communicate(text, "ar-SA-HamedNeural", rate="+5%")
    await communicate.save(out_mp3)

def _generate_voice(text: str, out_mp3: str):
    if FISH_KEY and MY_VOICE_ID:
        try:
            headers = {
                "Authorization": f"Bearer {FISH_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "reference_id": MY_VOICE_ID,
                "format": "mp3",
                "mp3_bitrate": 128
            }
            res = SESSION.post(FISH_TTS_URL, json=payload, headers=headers, timeout=25)
            if res.status_code == 200 and len(res.content) > 1000:
                with open(out_mp3, "wb") as f:
                    f.write(res.content)
                return
        except Exception:
            pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_fallback_tts(text, out_mp3))
    finally:
        loop.close()

def _fetch_scene_image(prompt_en: str, out_img: str, width=1280, height=720):
    encoded = urllib.parse.quote(f"{prompt_en}, cinematic lighting, ultra detailed, 8k, photorealistic, no text")
    url = f"{IMG_API}{encoded}?width={width}&height={height}&nologo=true&seed={int(time.time() * 100) % 99999}"
    try:
        res = SESSION.get(url, timeout=30)
        if res.status_code == 200 and len(res.content) > 5000:
            with open(out_img, "wb") as f:
                f.write(res.content)
            return True
    except Exception:
        pass
    img = Image.new("RGB", (width, height), (15, 23, 42))
    img.save(out_img)
    return False
def _compose_cinematic_frame(img_path: str, ar_caption: str, brand: str = "Albaraa AI OS"):
    _ensure_font()
    base = Image.open(img_path).convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.rectangle([(0, 520), (1280, 720)], fill=(10, 15, 30, 195))
    draw.rectangle([(0, 520), (1280, 526)], fill=(217, 119, 6, 255))
    draw.rounded_rectangle([(30, 25), (270, 70)], radius=12, fill=(15, 23, 42, 180))

    try:
        font_main = ImageFont.truetype(FONT_PATH, 38) if os.path.exists(FONT_PATH) else ImageFont.load_default()
        font_brand = ImageFont.truetype(FONT_PATH, 22) if os.path.exists(FONT_PATH) else ImageFont.load_default()
    except Exception:
        font_main = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    draw.text((55, 33), brand, font=font_brand, fill=(251, 191, 36, 255))

    shaped = _shape_ar(ar_caption[:85])
    x1, y1, x2, y2 = draw.textbbox((0, 0), shaped, font=font_main)
    text_w = x2 - x1
    x_pos = max(40, (1280 - text_w) // 2)
    draw.text((x_pos, 585), shaped, font=font_main, fill=(255, 255, 255, 255))

    final_img = Image.alpha_composite(base, overlay).convert("RGB")
    final_img.save(img_path, quality=92)

def _zoom_effect(clip, zoom_ratio=0.05):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        bw, bh = img.size
        scale = 1 + (zoom_ratio * (t / max(clip.duration, 0.1)))
        nw, nh = int(bw * scale), int(bh * scale)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - bw) // 2
        top = (nh - bh) // 2
        img = img.crop((left, top, left + bw, top + bh))
        return np.array(img)
    return clip.fl(effect)

def make_video(cid: str, msg: str):
    voice_label = "بصوتك الشخصي" if (FISH_KEY and MY_VOICE_ID) else "بصوت المذيع الذكي"
    send_msg(cid, f"🎬 جاري كتابة السيناريو وتوليد المشاهد السينمائية والتعليق الصوتي ({voice_label})...")
    sys_prompt = (
        "أنت مخرج أفلام وثائقية ومصمم موشن جرافيك. صمم سيناريو فيديو احترافي قصير من 4 مشاهد حول طلب المستخدم. "
        "أرجع النتيجة بصيغة JSON فقط بدون أي كلام خارجها بهذا الهيكل:\n"
        '{"video_title": "عنوان الفيديو", "scenes": ['
        '{"narration": "نص التعليق الصوتي بالعربية الفصحى جملة واحدة قوية", '
        '"caption": "عنوان قصير يظهر على الشاشة بالعربية", '
        '"visual_prompt": "Detailed cinematic scene description in English"}]}'
    )
    raw = ai_ask(msg, sys_prompt)
    data = _extract_json(raw)

    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    title = data.get("video_title", "Albaraa AI Production") if isinstance(data, dict) else "Albaraa AI Video"

    if not scenes:
        scenes = [
            {"narration": "مرحباً بكم في منظومة البراء للذكاء الاصطناعي المتكامل.", "caption": "منظومة Albaraa AI OS", "visual_prompt": "Futuristic artificial intelligence command center glowing blue gold"},
            {"narration": "نبتكر الحلول الذكية ونبني المستقبل بأحدث التقنيات.", "caption": "ابتكار وتطوير مستمر", "visual_prompt": "Advanced robotics and holographic data analytics dark room"}
        ]

    clips = []
    temp_files = []
    ts = int(time.time())

    try:
        for idx, sc in enumerate(scenes[:4]):
            img_p = f"/tmp/sc_{ts}_{idx}.jpg"
            aud_p = f"/tmp/au_{ts}_{idx}.mp3"
            temp_files.extend([img_p, aud_p])

            narration = sc.get("narration", "").strip()
            caption = sc.get("caption", narration[:50]).strip()
            v_prompt = sc.get("visual_prompt", "Modern artificial intelligence technology")

            _generate_voice(narration, aud_p)
            _fetch_scene_image(v_prompt, img_p)
            _compose_cinematic_frame(img_p, caption)

            audio_clip = AudioFileClip(aud_p)
            dur = max(audio_clip.duration + 0.4, 3.0)
            img_clip = ImageClip(img_p).set_duration(dur)
            img_clip = _zoom_effect(img_clip, zoom_ratio=0.05).set_audio(audio_clip)
            clips.append(img_clip)

        final_video = concatenate_videoclips(clips, method="compose")
        out_mp4 = f"/tmp/Albaraa_Video_{ts}.mp4"
        temp_files.append(out_mp4)

        final_video.write_videofile(
            out_mp4,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger=None
        )
        final_video.close()
        for c in clips:
            c.close()

        send_file(cid, out_mp4, "Albaraa_AI_Video.mp4", "video/mp4", f"🎬 *{title}*\nتم الإنتاج والمونتاج الآلي ({voice_label}) عبر منظومة Albaraa AI OS")
    except Exception as e:
        send_msg(cid, f"⚠️ تعذر إكمال مونتاج الفيديو: {str(e)[:120]}")
    finally:
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

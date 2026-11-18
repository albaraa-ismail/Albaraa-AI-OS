import os, asyncio
from pptx import Presentation
from pptx.util import Inches, Pt
import edge_tts
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import plotly.graph_objects as go
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from core_ai import ai_ask, send_msg, send_file
from office_tools import today_dates

def _ar_txt(text):
    return get_display(arabic_reshaper.reshape(str(text)))

async def _edge_voice(text, path):
    await edge_tts.Communicate(text, "ar-SA-HamedNeural").save(path)

def _make_audio(text, path):
    try: asyncio.run(_edge_voice(text, path))
    except Exception: gTTS(text=text, lang='ar').save(path)

def _make_modern_chart(title, labels, values, out_path):
    try:
        ar_labels = [_ar_txt(l[:20]) for l in labels]
        fig = go.Figure(data=[go.Bar(x=ar_labels, y=values, text=values, textposition='auto', marker_color=['#1B365D', '#2B5B84', '#3A82B5', '#4DA8DA', '#00B4D8'][:len(values)])])
        fig.update_layout(title=dict(text=_ar_txt(title[:50]), x=0.5, font=dict(size=20, color='#1B365D')), plot_bgcolor='white', paper_bgcolor='white', width=900, height=500)
        fig.write_image(out_path, scale=2)
        return os.path.exists(out_path)
    except Exception: return False

def make_ppt(cid, msg):
    send_msg(cid, "⏳ جاري تصميم عرض PowerPoint احترافي مزود برسوم بيانية عصرية...")
    raw = ai_ask(msg, "صمم عرضاً تقديمياً احترافياً من 10 شرائح متكاملة. اكتب عنوان كل شريحة في سطر، وتحته 4 نقاط تفصيلية مركزة، وافصل بين كل شريحة وأخرى بسطر فارغ تماماً:")
    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)

    s0 = prs.slides.add_slide(prs.slide_layouts[0])
    s0.shapes.title.text = msg[:65]
    if len(s0.placeholders) > 1:
        s0.placeholders[1].text = f"عرض تنفيذي ودراسة تحليلية | {today_dates()}"

    for blk in [x.strip() for x in raw.split("\n\n") if x.strip()]:
        lns = [l.strip().replace("**", "").lstrip("-*# ") for l in blk.split("\n") if l.strip()]
        if lns:
            sl = prs.slides.add_slide(prs.slide_layouts[1])
            sl.shapes.title.text = lns[0][:70]
            if len(sl.placeholders) > 1:
                tf = sl.placeholders[1].text_frame
                tf.text = lns[1] if len(lns) > 1 else ""
                for bullet in lns[2:6]:
                    p = tf.add_paragraph(); p.text = bullet; p.font.size = Pt(20)

    chart_img = "/tmp/modern_chart.png"
    if _make_modern_chart("مؤشرات الكفاءة والأداء والقياس", ["الجودة", "السرعة", "الدقة", "التكامل", "الأثر"], [96, 94, 98, 95, 97], chart_img):
        sc = prs.slides.add_slide(prs.slide_layouts[5])
        sc.shapes.title.text = "المؤشرات الإحصائية وقياس الأداء"
        sc.shapes.add_picture(chart_img, Inches(2.2), Inches(1.6), width=Inches(8.8))
        if os.path.exists(chart_img): os.remove(chart_img)

    path = "/tmp/Out.pptx"
    prs.save(path)
    send_file(cid, path, "Executive_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ العرض التقديمي الاحترافي جاهز")
    if os.path.exists(path): os.remove(path)

def make_video(cid, msg):
    send_msg(cid, "🎬 جاري إنتاج الفيديو الاحترافي بالصوت البشري والرسوم...")
    script = ai_ask(msg, "اكتب سيناريو فيديو احترافي متكامل من 7 مشاهد متسلسلة وطويلة. لكل مشهد اكتب سطراً واحداً بصيغة: العنوان | النص الصوتي المفصل (3 إلى 4 جمل كاملة باللغة العربية الفصحى الواضحة):")
    scenes = []
    for l in script.split("\n"):
        if "|" in l:
            parts = [p.strip().replace("**", "") for p in l.split("|") if p.strip()]
            if len(parts) >= 2: scenes.append((parts[0], parts[1]))
    if not scenes: scenes = [(msg[:35], script[:500])]

    clips, temp_files = [], []
    colors = [(15, 32, 56), (22, 52, 72), (28, 38, 64), (18, 48, 58), (25, 35, 55), (14, 42, 62), (20, 40, 65)]

    for idx, (title, voice_txt) in enumerate(scenes[:8]):
        img_path, aud_path = f"/tmp/sc_{idx}.png", f"/tmp/sc_{idx}.mp3"
        temp_files.extend([img_path, aud_path])
        _make_audio(voice_txt, aud_path)
        aud_clip = AudioFileClip(aud_path)

        img = Image.new("RGB", (1280, 720), color=colors[idx % len(colors)])
        draw = ImageDraw.Draw(img)
        try:
            f_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            f_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except Exception:
            f_title = f_body = ImageFont.load_default()

        draw.rectangle([40, 40, 1240, 680], outline=(110, 190, 255), width=3)
        draw.text((640, 130), _ar_txt(title[:45]), fill=(255, 215, 0), font=f_title, anchor="mm")

        words = voice_txt.split()
        lines = [" ".join(words[i:i+9]) for i in range(0, len(words), 9)]
        y_pos = 270
        for ln in lines[:6]:
            draw.text((640, y_pos), _ar_txt(ln), fill=(255, 255, 255), font=f_body, anchor="mm")
            y_pos += 55

        img.save(img_path)
        clips.append(ImageClip(img_path).set_duration(aud_clip.duration + 0.5).set_audio(aud_clip))

    final_vid = concatenate_videoclips(clips, method="compose")
    out_vid = "/tmp/Video_Out.mp4"
    final_vid.write_videofile(out_vid, fps=15, codec="libx264", audio_codec="aac", logger=None)
    send_file(cid, out_vid, "Video_Presentation.mp4", "video/mp4", "🎬 الفيديو جاهز")

    for f in temp_files + [out_vid]:
        if os.path.exists(f):
            try: os.remove(f)
            except Exception: pass

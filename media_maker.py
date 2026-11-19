import os, json, asyncio, subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import edge_tts
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import plotly.graph_objects as go
import imageio_ffmpeg
from core_ai import ai_ask, send_msg, send_file
from office_tools import today_dates

def _ar_txt(text):
    return get_display(arabic_reshaper.reshape(str(text)))

async def _edge_voice(text, path):
    await edge_tts.Communicate(text, "ar-SA-HamedNeural").save(path)

def _make_audio(text, path):
    try: asyncio.run(_edge_voice(text, path))
    except Exception: gTTS(text=text, lang='ar').save(path)

def _style_slide(slide, bg_rgb=(15, 28, 46)):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*bg_rgb)

def _make_dynamic_chart(msg, out_path):
    try:
        raw = ai_ask(msg, 'استخرج 5 مؤشرات رقمية واقعية مرتبطة بالموضوع بصيغة JSON فقط: {"title": "عنوان الرسم", "labels": ["أ", "ب", "ج", "د", "هـ"], "values": [80, 65, 90, 75, 85]}')
        d = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
        ar_labels = [_ar_txt(l[:18]) for l in d["labels"][:5]]
        fig = go.Figure(data=[go.Bar(x=ar_labels, y=d["values"][:5], text=d["values"][:5], textposition='auto', marker_color=['#00B4D8', '#0096C7', '#0077B6', '#48CAE4', '#90E0EF'])])
        fig.update_layout(title=dict(text=_ar_txt(d.get("title", "التحليل البياني")[:45]), x=0.5, font=dict(size=22, color='#FFD166')), plot_bgcolor='#0F1C2E', paper_bgcolor='#0F1C2E', font=dict(color='white', size=15), width=950, height=500)
        fig.write_image(out_path, scale=2)
        return os.path.exists(out_path)
    except Exception: return False

def make_ppt(cid, msg):
    send_msg(cid, "⏳ وكيل التصميم يبني عرضاً تقديمياً فاخراً بهوية بصرية متكاملة...")
    raw = ai_ask(msg, "صمم عرضاً تقديمياً احترافياً من 9 شرائح متكاملة. اكتب عنوان كل شريحة في سطر، وتحته 4 نقاط تفصيلية مركزة، وافصل بين كل شريحة وأخرى بسطر فارغ تماماً:")
    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)

    s0 = prs.slides.add_slide(prs.slide_layouts[6])
    _style_slide(s0, (10, 20, 36))
    tb = s0.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.3), Inches(2.5))
    tf0 = tb.text_frame; tf0.word_wrap = True
    p0 = tf0.paragraphs[0]; p0.text = msg[:70]; p0.font.size = Pt(40); p0.font.bold = True; p0.font.color.rgb = RGBColor(255, 209, 102)
    p1 = tf0.add_paragraph(); p1.text = f"\nدراسة وعرض تنفيذي متكامل | {today_dates()}"; p1.font.size = Pt(20); p1.font.color.rgb = RGBColor(200, 220, 240)

    for blk in [x.strip() for x in raw.split("\n\n") if x.strip()]:
        lns = [l.strip().replace("**", "").lstrip("-*# ") for l in blk.split("\n") if l.strip()]
        if lns:
            sl = prs.slides.add_slide(prs.slide_layouts[6])
            _style_slide(sl, (15, 28, 46))
            box = sl.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(6.2))
            tf = box.text_frame; tf.word_wrap = True
            t = tf.paragraphs[0]; t.text = lns[0][:75]; t.font.size = Pt(28); t.font.bold = True; t.font.color.rgb = RGBColor(255, 209, 102)
            for bullet in lns[1:6]:
                p = tf.add_paragraph(); p.text = f"▪ {bullet}"; p.font.size = Pt(20); p.font.color.rgb = RGBColor(240, 244, 248); p.space_before = Pt(14)

    chart_img = "/tmp/dyn_chart.png"
    if _make_dynamic_chart(msg, chart_img):
        sc = prs.slides.add_slide(prs.slide_layouts[6])
        _style_slide(sc, (15, 28, 46))
        sc.shapes.add_picture(chart_img, Inches(1.8), Inches(1.1), width=Inches(9.6))
        if os.path.exists(chart_img): os.remove(chart_img)

    path = "/tmp/Out.pptx"
    prs.save(path)
    send_file(cid, path, "Executive_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ العرض التقديمي الفاخر جاهز")
    if os.path.exists(path): os.remove(path)

def make_video(cid, msg):
    send_msg(cid, "🎬 استوديو الإنتاج يجهز الفيديو بالصوت السعودي والتصميم البصري...")
    script = ai_ask(msg, "اكتب سيناريو فيديو احترافي من 6 مشاهد متسلسلة. لكل مشهد اكتب سطراً واحداً بصيغة: العنوان | النص الصوتي المفصل (3 جمل كاملة باللغة العربية الفصحى):")
    scenes = [tuple(p.strip().replace("**", "") for p in l.split("|") if p.strip())[:2] for l in script.split("\n") if "|" in l and len(l.split("|")) >= 2]
    if not scenes: scenes = [(msg[:35], script[:400])]

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    seg_files, temp_files = [], []
    colors = [(12, 24, 42), (18, 38, 60), (22, 30, 52), (14, 42, 54), (20, 28, 48), (10, 32, 50)]

    for idx, (title, voice_txt) in enumerate(scenes[:6]):
        img_path, aud_path, seg_path = f"/tmp/sc_{idx}.png", f"/tmp/sc_{idx}.mp3", f"/tmp/seg_{idx}.mp4"
        temp_files.extend([img_path, aud_path, seg_path])
        _make_audio(voice_txt, aud_path)

        img = Image.new("RGB", (854, 480), color=colors[idx % len(colors)])
        draw = ImageDraw.Draw(img)
        try:
            f_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            f_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except Exception:
            f_title = f_body = ImageFont.load_default()

        draw.rectangle([30, 30, 824, 450], outline=(255, 209, 102), width=2)
        draw.text((427, 80), _ar_txt(title[:42]), fill=(255, 209, 102), font=f_title, anchor="mm")
        words = voice_txt.split()
        for i, ln in enumerate([" ".join(words[j:j+8]) for j in range(0, len(words), 8)][:6]):
            draw.text((427, 175 + i*38), _ar_txt(ln), fill=(240, 244, 248), font=f_body, anchor="mm")

        img.save(img_path)
        subprocess.run([ffmpeg, "-y", "-loop", "1", "-i", img_path, "-i", aud_path, "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest", seg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(seg_path): seg_files.append(seg_path)

    list_file = "/tmp/concat.txt"; temp_files.append(list_file)
    with open(list_file, "w") as f:
        for s in seg_files: f.write(f"file '{s}'\n")
    out_vid = "/tmp/Video_Out.mp4"
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(out_vid): send_file(cid, out_vid, "Video_Presentation.mp4", "video/mp4", "🎬 الفيديو جاهز")
    for f in temp_files + [out_vid]:
        if os.path.exists(f):
            try: os.remove(f)
            except Exception: pass

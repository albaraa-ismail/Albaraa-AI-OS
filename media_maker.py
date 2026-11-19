import os, json, asyncio, subprocess, gc
from core_ai import ai_ask, send_msg, send_file
from office_tools import today_dates

def _ar_txt(text):
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(str(text)))

async def _edge_voice(text, path):
    import edge_tts
    await edge_tts.Communicate(text, "ar-SA-HamedNeural").save(path)

def _make_audio(text, path):
    try: asyncio.run(_edge_voice(text, path))
    except Exception:
        from gtts import gTTS
        gTTS(text=text, lang='ar').save(path)

def _style_slide(slide, bg_rgb=(15, 28, 46)):
    from pptx.dml.color import RGBColor
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*bg_rgb)

def _make_dynamic_chart(msg, research_data, out_path):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        prompt_json = (
            "استخرج 5 مؤشرات رقمية واقعية ومنطقية حول الموضوع بصيغة JSON فقط بدون أي نص إضافي:\n"
            '{"title": "عنوان التحليل البياني", "labels": ["المؤشر 1", "المؤشر 2", "المؤشر 3", "المؤشر 4", "المؤشر 5"], "values": [78, 85, 92, 68, 95]}'
        )
        raw = ai_ask(f"الموضوع: {msg}\nالبيانات:\n{research_data}", prompt_json)
        d = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
        ar_labels = [_ar_txt(l[:18]) for l in d.get("labels", [])[:5]]
        vals = d.get("values", [])[:5]

        fig, ax = plt.subplots(figsize=(10, 5.2), dpi=160)
        fig.patch.set_facecolor('#0F1C2E')
        ax.set_facecolor('#16263E')
        bars = ax.bar(ar_labels, vals, color=['#00B4D8', '#0096C7', '#0077B6', '#48CAE4', '#FFD166'], width=0.48)
        ax.set_title(_ar_txt(d.get("title", "مؤشرات الأداء والتحليل")[:48]), color='#FFD166', fontsize=17, fontweight='bold', pad=18)
        ax.tick_params(colors='white', labelsize=11)
        ax.grid(axis='y', linestyle='--', alpha=0.2, color='white')
        for spine in ax.spines.values(): spine.set_visible(False)
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + (max(vals)*0.02), str(yval), ha='center', va='bottom', color='#FFD166', fontweight='bold', fontsize=12)

        plt.tight_layout()
        plt.savefig(out_path, facecolor='#0F1C2E')
        plt.close(fig)
        gc.collect()
        return os.path.exists(out_path)
    except Exception as e:
        print("Chart Err:", e, flush=True)
        return False

def make_ppt(cid, msg):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    from duckduckgo_search import DDGS

    send_msg(cid, "👥 *تفعيل غرفة عمليات العرض التقديمي:*\n1️⃣ وكيل البحث يجمع أحدث البيانات...\n2️⃣ وكيل البناء يصيغ الشرائح التنفيذية...\n3️⃣ وكيل التصميم يبني الهوية البصرية والمخططات...")
    web = ""
    try:
        with DDGS() as dd:
            results = list(dd.text(msg, max_results=4))
            web = "\n".join([x.get("body", "") for x in results])
    except Exception: pass

    clean_title = ai_ask(msg, "صغ عنواناً تنفيذياً احترافياً من 4 إلى 7 كلمات لهذا العرض التقديمي. اكتب العنوان مباشرة بدون علامات تنصيص:").replace('"', '').strip()[:65]
    if "تعذر" in clean_title or len(clean_title) < 4:
        clean_title = msg[:55]

    raw = ai_ask(
        f"الموضوع: {clean_title}\nالطلب الأصلي: {msg}\nبيانات مساندة:\n{web}",
        "أنت مستشار استراتيجي. أنشئ 8 شرائح تنفيذية عميقة وغنية بالأرقام والنسب المئوية والحقائق العملية. افصل بين كل شريحة وأخرى بعلامة === فقط.\n"
        "التزم بهذه الصيغة لكل شريحة:\n"
        "عنوان الشريحة\n"
        "نقطة تنفيذية مركزة تتضمن رقماً أو نسبة أو معياراً واضحاً\n"
        "نقطة تنفيذية ثانية غنية بالمعلومات\n"
        "نقطة تنفيذية ثالثة قابلة للتطبيق\n"
        "نقطة تنفيذية رابعة تلخص الأثر\n"
        "ممنوع كتابة مقدمات أو ترقيم الشرائح بـ (الشريحة 1)."
    )

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    s0 = prs.slides.add_slide(blank)
    _style_slide(s0, (10, 20, 36))
    accent_bar = s0.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.18))
    accent_bar.fill.solid(); accent_bar.fill.fore_color.rgb = RGBColor(255, 209, 102); accent_bar.line.fill.background()

    tb = s0.shapes.add_textbox(Inches(1), Inches(2.3), Inches(11.3), Inches(3.0))
    tf0 = tb.text_frame; tf0.word_wrap = True
    p0 = tf0.paragraphs[0]
    p0.text = clean_title
    p0.alignment = PP_ALIGN.CENTER
    p0.font.size = Pt(42); p0.font.bold = True; p0.font.color.rgb = RGBColor(255, 209, 102)

    p1 = tf0.add_paragraph()
    p1.text = f"\nدراسة استراتيجية وتحليل تنفيذي شامل  |  {today_dates()}"
    p1.alignment = PP_ALIGN.CENTER
    p1.font.size = Pt(20); p1.font.color.rgb = RGBColor(200, 220, 240)

    blocks = [b.strip() for b in raw.split("===") if len(b.strip()) > 15]
    slide_num = 1
    for blk in blocks[:8]:
        lns = [l.strip().replace("**", "").lstrip("-*#▪•1234567890. ") for l in blk.split("\n") if len(l.strip()) > 3]
        if len(lns) >= 2:
            sl = prs.slides.add_slide(blank)
            _style_slide(sl, (15, 28, 46))

            hdr = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
            hdr.fill.solid(); hdr.fill.fore_color.rgb = RGBColor(22, 42, 68); hdr.line.fill.background()

            t_box = sl.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.7))
            t_tf = t_box.text_frame; t_tf.word_wrap = True
            t_p = t_tf.paragraphs[0]
            t_p.text = f"{slide_num}. {lns[0][:70]}"
            t_p.alignment = PP_ALIGN.RIGHT
            t_p.font.size = Pt(28); t_p.font.bold = True; t_p.font.color.rgb = RGBColor(255, 209, 102)

            card = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5.3))
            card.fill.solid(); card.fill.fore_color.rgb = RGBColor(20, 36, 58)
            card.line.color.rgb = RGBColor(45, 75, 115)

            box = sl.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(11.3), Inches(4.9))
            tf = box.text_frame; tf.word_wrap = True
            first = True
            for bullet in lns[1:5]:
                p = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                p.text = f"{bullet}  ◆"
                p.alignment = PP_ALIGN.RIGHT
                p.font.size = Pt(20); p.font.color.rgb = RGBColor(240, 244, 248); p.space_before = Pt(18)
            slide_num += 1

    chart_img = "/tmp/dyn_chart.png"
    if _make_dynamic_chart(clean_title, web, chart_img):
        sc = prs.slides.add_slide(blank)
        _style_slide(sc, (15, 28, 46))
        sc.shapes.add_picture(chart_img, Inches(1.5), Inches(0.9), width=Inches(10.3))
        if os.path.exists(chart_img): os.remove(chart_img)

    path = "/tmp/Out.pptx"
    prs.save(path)
    send_file(cid, path, "Executive_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", f"📽️ تم إنجاز العرض التنفيذي: *{clean_title}*\n💡 هل تود تحويل هذا العرض إلى فيديو بصوت بشري أو تقرير Word مفصل؟")
    if os.path.exists(path): os.remove(path)
    del prs; gc.collect()

def make_video(cid, msg):
    from PIL import Image, ImageDraw, ImageFont
    import imageio_ffmpeg

    send_msg(cid, "🎬 *غرفة إنتاج الفيديو:*\n1️⃣ وكيل البحث يجمع الحقائق...\n2️⃣ وكيل السيناريو يكتب المشاهد...\n3️⃣ استوديو الصوت والصورة يدمج المقطع...")
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

        draw.rectangle((40, 40, 814, 440), outline=(255, 209, 102), width=2)
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

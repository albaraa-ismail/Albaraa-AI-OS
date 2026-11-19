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

        prompt_json = 'استخرج 5 مؤشرات رقمية واقعية من البيانات بصيغة JSON فقط: {"title": "عنوان الرسم", "labels": ["أ", "ب", "ج", "د", "هـ"], "values": [85, 90, 78, 92, 88]}'
        raw = ai_ask(f"الموضوع: {msg}\nالبيانات:\n{research_data}", prompt_json)
        d = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
        ar_labels = [_ar_txt(l[:18]) for l in d.get("labels", [])[:5]]
        vals = d.get("values", [])[:5]

        fig, ax = plt.subplots(figsize=(9.5, 5), dpi=150)
        fig.patch.set_facecolor('#0F1C2E')
        ax.set_facecolor('#0F1C2E')
        bars = ax.bar(ar_labels, vals, color=['#00B4D8', '#0096C7', '#0077B6', '#48CAE4', '#90E0EF'], width=0.5)
        ax.set_title(_ar_txt(d.get("title", "التحليل البياني")[:45]), color='#FFD166', fontsize=16, pad=15)
        ax.tick_params(colors='white', labelsize=11)
        for spine in ax.spines.values(): spine.set_visible(False)
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 1, str(yval), ha='center', va='bottom', color='white', fontsize=11)

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
    from duckduckgo_search import DDGS

    send_msg(cid, "👥 *تفعيل غرفة عمليات العرض التقديمي:*\n1️⃣ وكيل البحث يجمع أحدث البيانات...\n2️⃣ وكيل البناء يصيغ الشرائح التنفيذية...\n3️⃣ وكيل الحوكمة يضبط الهوية البصرية...")
    web = ""
    try:
        with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text(msg, max_results=3)])
    except Exception: pass

    clean_title = ai_ask(msg, "اكتب عنواناً رسمياً فخماً ومختصراً لهذا العرض التقديمي (من 4 إلى 7 كلمات فقط بدون أي مقدمات أو رموز):").replace('"', '').strip()[:65]
    raw = ai_ask(
        f"الموضوع: {clean_title}\nبيانات البحث:\n{web}",
        "أنت وكيل البناء التنفيذي. أنشئ 8 شرائح احترافية عميقة المحتوى. افصل بين كل شريحة وأخرى بعلامة === فقط.\n"
        "صيغة كل شريحة:\nعنوان الشريحة\nنقطة تفصيلية غنية بالمعلومات\nنقطة تفصيلية ثانية\nنقطة تفصيلية ثالثة\nنقطة تفصيلية رابعة\n"
        "ممنوع كتابة مقدمات أو ترقيم الشرائح بـ (الشريحة 1)."
    )

    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    s0 = prs.slides.add_slide(blank)
    _style_slide(s0, (10, 20, 36))
    tb = s0.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.3), Inches(2.5))
    tf0 = tb.text_frame; tf0.word_wrap = True
    p0 = tf0.paragraphs[0]; p0.text = clean_title; p0.alignment = PP_ALIGN.CENTER; p0.font.size = Pt(42); p0.font.bold = True; p0.font.color.rgb = RGBColor(255, 209, 102)
    p1 = tf0.add_paragraph(); p1.text = f"\nدراسة وتحليل تنفيذي | {today_dates()}"; p1.alignment = PP_ALIGN.CENTER; p1.font.size = Pt(20); p1.font.color.rgb = RGBColor(200, 220, 240)

    blocks = [b.strip() for b in raw.split("===") if len(b.strip()) > 15]
    for blk in blocks[:9]:
        lns = [l.strip().replace("**", "").lstrip("-*#▪•1234567890. ") for l in blk.split("\n") if len(l.strip()) > 3]
        if len(lns) >= 2:
            sl = prs.slides.add_slide(blank)
            _style_slide(sl, (15, 28, 46))
            box = sl.shapes.add_textbox(Inches(0.9), Inches(0.7), Inches(11.5), Inches(6.0))
            tf = box.text_frame; tf.word_wrap = True
            t = tf.paragraphs[0]; t.text = lns[0][:75]; t.alignment = PP_ALIGN.RIGHT; t.font.size = Pt(30); t.font.bold = True; t.font.color.rgb = RGBColor(255, 209, 102)
            for bullet in lns[1:5]:
                p = tf.add_paragraph(); p.text = f"{bullet}  ▪"; p.alignment = PP_ALIGN.RIGHT; p.font.size = Pt(21); p.font.color.rgb = RGBColor(240, 244, 248); p.space_before = Pt(18)

    chart_img = "/tmp/dyn_chart.png"
    if _make_dynamic_chart(clean_title, web, chart_img):
        sc = prs.slides.add_slide(blank)
        _style_slide(sc, (15, 28, 46))
        sc.shapes.add_picture(chart_img, Inches(1.8), Inches(1.1), width=Inches(9.6))
        if os.path.exists(chart_img): os.remove(chart_img)

    path = "/tmp/Out.pptx"
    prs.save(path)
    send_file(cid, path, "Executive_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", f"📽️ تم إنجاز العرض عبر 3 وكلاء متخصصين: *{clean_title}*\n💡 هل تود تحويل هذا العرض إلى فيديو بصوت بشري أو تقرير Word مفصل؟")
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
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(out_vid): send_file(cid, out_vid, "Video_Presentation.mp4", "video/mp4", "🎬 الفيديو الاحترافي جاهز")
    for f in temp_files + [out_vid]:
        if os.path.exists(f):
            try: os.remove(f)
            except Exception: pass
    gc.collect()

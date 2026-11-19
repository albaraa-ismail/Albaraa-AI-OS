import os, gc, pendulum
from hijridate import Gregorian
from core_ai import sb, ai_ask, send_msg, send_file

def today_dates():
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ - {now.format('YYYY/MM/DD')}م"

def _clean_title(msg):
    t = ai_ask(msg, "حول الطلب إلى عنوان تقرير مؤسسي فخم من 3 إلى 6 كلمات بدون أفعال أمر. العنوان فقط:").replace('"', '').strip()[:60]
    if "تعذر" in t or len(t) < 4:
        for w in ("عطني", "أعطني", "اعطني", "صمم", "اكتب", "سوي", "اعمل", "أريد", "ابي", "أبي", "لوحة تحكم"):
            msg = msg.replace(w, "")
        t = msg.strip()[:55] or "منظومة مؤشرات الأداء المؤسسي"
    return t

def _set_rtl(p):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p._p.get_or_add_pPr().append(OxmlElement('w:bidi'))

def make_kpi(cid):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(["رقم العملية", "المستخدم", "القسم", "زمن التنفيذ(ث)", "الوقت الموفر(د)", "مؤشر التطور%", "المخرج"])
    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50"):
        ws.append([i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")])
    path = "/tmp/KPI.xlsx"; wb.save(path)
    send_file(cid, path, "Performance_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"📊 تقرير قياس الأداء ({today_dates()})")
    if os.path.exists(path): os.remove(path)
    del wb; gc.collect()

def make_word(cid, msg):
    from docx import Document
    from docx.shared import Pt as DocPt
    send_msg(cid, "👥 *تفعيل غرفة عمليات الوثائق:* جاري بناء الهيكل وتحرير المحاور التنفيذية...")
    title = _clean_title(msg)
    outline = ai_ask(msg, "ضع 5 محاور رئيسية لتغطية هذا الموضوع بعمق تنفيذي. اكتب كل محور في سطر مستقل:")
    sections = [s.strip().lstrip("-*#1234567890. ") for s in outline.split("\n") if len(s.strip()) > 3][:5] or ["الإطار العام", "التحليل", "التطبيقات", "المؤشرات", "التوصيات"]

    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'; doc.styles['Normal'].font.size = DocPt(14)
    _set_rtl(doc.add_heading(title, 0)); _set_rtl(doc.add_paragraph(f"تاريخ الإصدار: {today_dates()}"))
    for sec in sections:
        _set_rtl(doc.add_heading(sec, level=1))
        content = ai_ask(f"الموضوع: {title}\nالمحور: {sec}", "اكتب محتوى تنفيذياً غزيراً ومفصلاً باللغة العربية الفصحى:")
        for l in content.split("\n"):
            cl = l.strip().replace("**", "")
            if not cl: continue
            if cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً")): _set_rtl(doc.add_heading(cl.lstrip("# "), level=2))
            else: _set_rtl(doc.add_paragraph(cl))
    path = "/tmp/Doc.docx"; doc.save(path)
    send_file(cid, path, "Executive_Document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📄 تم إعداد المستند الاحترافي: *{title}*")
    if os.path.exists(path): os.remove(path)
    del doc; gc.collect()

def make_excel(cid, msg):
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import arabic_reshaper; from bidi.algorithm import get_display

    send_msg(cid, "👥 *هندسة لوحة القيادة المؤسسية:* جاري بناء قاعدة البيانات، المؤشرات، والرسوم البيانية...")
    prompt = (
        "أنت مدير تحليلات أداء مؤسسي. أنشئ 3 أقسام مفصولة بسطر === فقط:\n"
        "1: عنوان مؤسسي رسمي للتقرير (3 إلى 6 كلمات بدون أفعال أمر).\n"
        "2: جدول بيانات من 9 صفوف (صف عناوين + 8 صفوف بيانات واقعية) بـ 6 أعمدة مفصولة بـ | فقط:\n"
        "الاسم أو البند | المسمى الوظيفي | الإدارة | المحقق الفعلي (رقم 75-115) | المستهدف (رقم 85-100) | الإجراء التطويري\n"
        "3: ملخص تنفيذي من 3 توصيات استراتيجية بدون رموز نجمية.\n"
        "التزم بالفصل بـ === بدون مقدمات."
    )
    res = ai_ask(msg, prompt)
    it_p = iter([p.strip() for p in res.split("===") if p.strip()])
    p1, p2, p3 = next(it_p, ""), next(it_p, ""), next(it_p, "")
    title = p1.replace('"', '').strip()[:55] if (p1 and len(p1) < 85 and "|" not in p1) else "تقرير تقييم الأداء والكفاءة المؤسسية"
    raw = p2 if "|" in p2 else res
    summary = p3 or "1. تعزيز برامج التطوير المهني للوحدات دون المستهدف.\n2. ربط الحوافز الفصلية بمؤشرات الإنجاز الفعلية.\n3. تعميم أفضل الممارسات التشغيلية."
    wb = openpyxl.Workbook()
    ws_dash = wb.active; ws_dash.title = "لوحة القيادة"; ws_dash.sheet_view.rightToLeft = True; ws_dash.sheet_view.showGridLines = False
    ws_data = wb.create_sheet("سجل البيانات والتحليل"); ws_data.sheet_view.rightToLeft = True

    f_navy = PatternFill(start_color="0B192C", end_color="0B192C", fill_type="solid")
    f_slate = PatternFill(start_color="1E3E62", end_color="1E3E62", fill_type="solid")
    f_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    f_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    f_green = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    f_blue = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    f_amber = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    brd = Border(left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'), top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1'))
    aln_c = Alignment(horizontal="center", vertical="center", wrap_text=True)
    aln_r = Alignment(horizontal="right", vertical="center", wrap_text=True)
    parsed = []
    for l in raw.split("\n"):
        if "|" in l and not set(l.replace("|", "").strip()).issubset({"-", ":", " "}):
            vals = []
            for x in l.split("|"):
                v = x.strip().replace("**", "")
                if v and len(vals) < 6:
                    try: v = float(v) if "." in v else int(v)
                    except ValueError: pass
                    vals.append(v)
            if len(vals) >= 5: parsed.append(vals)

    if len(parsed) < 2:
        parsed = [["الاسم", "المسمى", "الإدارة", "المحقق", "المستهدف", "الإجراء"], ["سارة القحطاني", "أخصائي أول", "الموارد البشرية", 98, 90, "ترشيح للقيادة"], ["عبدالله العتيبي", "مهندس مشاريع", "العمليات", 92, 95, "تحسين الجدولة"], ["نورة الشمري", "محلل مالي", "المالية", 104, 100, "تعميم النموذج"]]

    headers = ["الرقم الوظيفي", "الاسم / البند", "المسمى الوظيفي", "الإدارة", "المحقق الفعلي", "المستهدف", "الإنجاز %", "الفارق", "التقييم المعتمد", "خطة التطوير"]
    ws_data.row_dimensions.height = 32
    for c_i, h in enumerate(headers, 1):
        c = ws_data.cell(1, c_i, h); c.fill = f_navy; c.font = Font(color="FFD166", size=11, bold=True); c.alignment = aln_c; c.border = brd

    it_rows = iter(parsed); next(it_rows, None)
    rows = list(it_rows); last_r = len(rows) + 1
    chart_labels, chart_act, chart_tgt = [], [], []
    sum_ac, sum_tg, sum_pct, pass_cnt = 0, 0, 0.0, 0

    for idx, r in enumerate(rows, 2):
        ws_data.row_dimensions[idx].height = 26
        it_c = iter(r)
        nm, role_t, dp = str(next(it_c, "موظف")), str(next(it_c, "أخصائي")), str(next(it_c, "العمليات"))
        raw_ac, raw_tg, act_plan = next(it_c, 88), next(it_c, 90), str(next(it_c, "متابعة دورية"))
        ac = raw_ac if isinstance(raw_ac, (int, float)) else 88
        tg = raw_tg if isinstance(raw_tg, (int, float)) else 90
        pct = round((ac / max(tg, 1)) * 100, 1); diff = round(ac - tg, 1)
        eval_txt = "متفوق 🌟" if pct >= 100 else ("جيد جداً ✅" if pct >= 85 else "يحتاج تطوير ⚠️")
        sum_ac += ac; sum_tg += tg; sum_pct += pct
        if pct >= 85: pass_cnt += 1
        if len(chart_labels) < 7:
            chart_labels.append(get_display(arabic_reshaper.reshape(nm[:13]))); chart_act.append(ac); chart_tgt.append(tg)
        entries = [f"EMP-{100+idx}", nm, role_t, dp, ac, tg, f"{pct}%", f"{'+' if diff > 0 else ''}{diff}", eval_txt, act_plan]
        for c_i, val in enumerate(entries, 1):
            c = ws_data.cell(idx, c_i, val); c.border = brd; c.font = Font(color="0F172A", size=11, bold=(c_i in (1, 2, 7, 9))); c.alignment = aln_c if c_i in (1, 5, 6, 7, 8, 9) else aln_r
            if idx % 2 == 0: c.fill = f_zebra
            if c_i == 9: c.fill = f_green if pct >= 100 else (f_blue if pct >= 85 else f_amber)
    cnt = max(len(rows), 1); avg_pct = round(sum_pct / cnt, 1); tot_diff = round(sum_ac - sum_tg, 1)
    tot_r = last_r + 1; ws_data.row_dimensions.height = 30
    tots = ["الإجمالي", f"{cnt} سجل", "كافة الفئات", "جميع الإدارات", round(sum_ac, 1), round(sum_tg, 1), f"{avg_pct}%", f"{'+' if tot_diff > 0 else ''}{tot_diff}", f"{pass_cnt} محقق", "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val); c.fill = f_slate; c.font = Font(color="FFFFFF", size=11, bold=True); c.alignment = aln_c; c.border = brd

    for c_i in range(1, 11): ws_data.column_dimensions[get_column_letter(c_i)].width = 25 if c_i in (2, 10) else (19 if c_i in (3, 4, 9) else 15)
    for c in range(1, 14): ws_dash.column_dimensions[get_column_letter(c)].width = 14

    ws_dash.merge_cells("B2:M3"); ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"; ws_dash["B2"].fill = f_navy; ws_dash["B2"].font = Font(color="FFD166", size=18, bold=True); ws_dash["B2"].alignment = aln_c
    ws_dash.merge_cells("B4:M4"); ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  بطاقة الأداء المتوازن والمؤشرات التشغيلية"; ws_dash["B4"].fill = f_slate; ws_dash["B4"].font = Font(color="FFFFFF", size=11); ws_dash["B4"].alignment = aln_c

    cards = [("B", "D", "إجمالي الأداء المحقق", f"{round(sum_ac, 1)}", "1E3A8A"), ("E", "G", "متوسط نسبة الإنجاز", f"{avg_pct}%", "0F766E"), ("H", "J", "الفارق عن المستهدف", f"{'+' if tot_diff > 0 else ''}{tot_diff}", "B45309"), ("K", "M", "نسبة المحققين للمعيار", f"{round((pass_cnt/cnt)*100)}%", "4338CA")]
    ws_dash.row_dimensions.height = 26; ws_dash.row_dimensions.height = 40
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6"); ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value = tk; ws_dash[f"{cs}6"].fill = PatternFill(start_color=hx, end_color=hx, fill_type="solid"); ws_dash[f"{cs}6"].font = Font(color="FFFFFF", size=11, bold=True); ws_dash[f"{cs}6"].alignment = aln_c
        ws_dash[f"{cs}7"].value = fk; ws_dash[f"{cs}7"].fill = f_white; ws_dash[f"{cs}7"].font = Font(color=hx, size=18, bold=True); ws_dash[f"{cs}7"].alignment = aln_c; ws_dash[f"{cs}7"].border = brd

    for r_idx in range(9, 27): ws_dash.row_dimensions[r_idx].height = 20
    chart_img = "/tmp/dash_chart.png"
    try:
        fig, ax = plt.subplots(figsize=(10.5, 4.3), dpi=130)
        fig.patch.set_facecolor('#0B192C'); ax.set_facecolor('#132743')
        x_pos = range(len(chart_labels))
        b1 = ax.bar([p - 0.18 for p in x_pos], chart_act, width=0.35, label=get_display(arabic_reshaper.reshape("المحقق الفعلي")), color='#00B4D8')
        b2 = ax.bar([p + 0.18 for p in x_pos], chart_tgt, width=0.35, label=get_display(arabic_reshaper.reshape("المستهدف المخطط")), color='#FFD166')
        ax.set_xticks(list(x_pos)); ax.set_xticklabels(chart_labels)
        ax.set_title(get_display(arabic_reshaper.reshape("مقارنة الأداء المحقق مقابل المستهدف")), color='#FFD166', fontsize=14, fontweight='bold', pad=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.legend(facecolor='#0B192C', edgecolor='none', labelcolor='white', fontsize=10)
        for sp in ax.spines.values(): sp.set_visible(False)
        for b in b1:
            yv = b.get_height()
            ax.text(b.get_x() + b.get_width()/2, yv + 1, str(yv), ha='center', va='bottom', color='#00B4D8', fontsize=9, fontweight='bold')
        plt.tight_layout(); plt.savefig(chart_img, facecolor='#0B192C'); plt.close(fig)
        if os.path.exists(chart_img):
            img_xl = XLImage(chart_img); img_xl.width = 820; img_xl.height = 330
            ws_dash.add_image(img_xl, "B9")
    except Exception as e: print("Chart Img Err:", e, flush=True)

    clean_sum = summary.replace("**", "").replace("###", "").replace("##", "").strip()
    ws_dash.merge_cells("B27:M27"); ws_dash["B27"] = "💡 القراءة التحليلية والتوصيات التنفيذية للإدارة"; ws_dash["B27"].fill = f_navy; ws_dash["B27"].font = Font(color="FFD166", size=12, bold=True); ws_dash["B27"].alignment = aln_r
    ws_dash.row_dimensions.height = 28
    ws_dash.merge_cells("B28:M33"); ws_dash["B28"] = clean_sum; ws_dash["B28"].fill = f_white; ws_dash["B28"].font = Font(color="1E293B", size=11); ws_dash["B28"].alignment = Alignment(horizontal="right", vertical="top", wrap_text=True); ws_dash["B28"].border = brd

    path = "/tmp/Executive_Dashboard.xlsx"; wb.save(path)
    send_file(cid, path, "Executive_Dashboard.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"📊 تم إعداد لوحة القيادة المؤسسية: *{title}*\n✨ تشمل: 4 بطاقات مؤشرات + سجل الموظفين وخطة التطوير.")
    if os.path.exists(chart_img): send_file(cid, chart_img, "Performance_Chart.png", "image/png", f"📈 الرسم البياني لمؤشرات: *{title}*")
    for f in (path, chart_img):
        if os.path.exists(f): os.remove(f)
    del wb; gc.collect()
def make_pptx(cid, msg):
    import json
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    send_msg(cid, "📊 *تفعيل استوديو العروض التقديمية:* جاري تصميم الشرائح وتنسيق الهوية البصرية...")
    title = _clean_title(msg)

    prompt = (
        f"أنت خبير تصميم عروض تقديمية تنفيذية. أنشئ محتوى عرض تقديمي احترافي حول: {msg}\n"
        "يجب أن يكون الرد بصيغة JSON صالحة فقط بدون أي نص إضافي أو علامات markdown، بالهيكل التالي تماماً:\n"
        '{"subtitle": "وصف مختصر جذاب للعرض", "slides": [{"heading": "عنوان الشريحة", "points": ["نقطة رئيسية واضحة ومفيدة", "نقطة ثانية", "نقطة ثالثة", "نقطة رابعة"]}]}\n'
        "أنشئ 6 شرائح متنوعة وشاملة باللغة العربية الفصحى."
    )

    raw = ai_ask(msg, prompt).replace("```json", "").replace("```", "").strip()
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
    except Exception:
        data = {
            "subtitle": "عرض تحليلي واستراتيجي شامل",
            "slides": [
                {"heading": "نظرة عامة وأهداف العرض", "points": ["تحديد الرؤية والأهداف الاستراتيجية", "تحليل الوضع الراهن والفرص المتاحة", "رفع كفاءة الأداء وجودة المخرجات"]},
                {"heading": "المحاور الرئيسية للتنفيذ", "points": ["التخطيط المنهجي وتوزيع المهام", "توظيف التقنيات الحديثة والأتمتة", "المتابعة المستمرة وقياس الأثر"]},
                {"heading": "التوصيات والخطوات القادمة", "points": ["البدء الفوري بالمرحلة الأولى", "مراجعة مؤشرات الأداء بشكل دوري", "تطوير المبادرات بناءً على النتائج"]}
            ]
        }

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    NAVY = RGBColor(11, 25, 44)
    SLATE = RGBColor(30, 62, 98)
    GOLD = RGBColor(255, 209, 102)
    WHITE = RGBColor(255, 255, 255)
    LIGHT_BG = RGBColor(248, 250, 252)
    DARK_TXT = RGBColor(15, 23, 42)

    s0 = prs.slides.add_slide(blank_layout)
    bg0 = s0.background.fill
    bg0.solid()
    bg0.fore_color.rgb = NAVY

    bar = s0.shapes.add_shape(1, Inches(0), Inches(6.8), Inches(13.333), Inches(0.2))
    bar.fill.solid()
    bar.fill.fore_color.rgb = GOLD
    bar.line.fill.background()

    tb = s0.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.RIGHT
    p.font.name = "Arial"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = GOLD

    p_sub = tf.add_paragraph()
    p_sub.text = data.get("subtitle", "")
    p_sub.alignment = PP_ALIGN.RIGHT
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(20)
    p_sub.font.color.rgb = WHITE
    p_sub.space_before = Pt(14)

    p_dt = tf.add_paragraph()
    p_dt.text = f"تاريخ الإصدار: {today_dates()} | Albaraa AI OS"
    p_dt.alignment = PP_ALIGN.RIGHT
    p_dt.font.name = "Arial"
    p_dt.font.size = Pt(14)
    p_dt.font.color.rgb = RGBColor(148, 163, 184)
    p_dt.space_before = Pt(28)
    for idx, sl in enumerate(data.get("slides", [])[:8], 1):
        slide = prs.slides.add_slide(blank_layout)
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = LIGHT_BG

        hdr = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = NAVY
        hdr.line.fill.background()

        accent = slide.shapes.add_shape(1, Inches(0), Inches(1.2), Inches(13.333), Inches(0.08))
        accent.fill.solid()
        accent.fill.fore_color.rgb = GOLD
        accent.line.fill.background()

        htb = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.7))
        htf = htb.text_frame
        hp = htf.paragraphs[0]
        hp.text = f"{idx}. {sl.get('heading', '')}"
        hp.alignment = PP_ALIGN.RIGHT
        hp.font.name = "Arial"
        hp.font.size = Pt(26)
        hp.font.bold = True
        hp.font.color.rgb = GOLD

        btb = slide.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.8))
        btf = btb.text_frame
        btf.word_wrap = True
        for p_i, pt_text in enumerate(sl.get("points", [])):
            bp = btf.paragraphs[0] if p_i == 0 else btf.add_paragraph()
            bp.text = f"▪ {pt_text}"
            bp.alignment = PP_ALIGN.RIGHT
            bp.font.name = "Arial"
            bp.font.size = Pt(20)
            bp.font.color.rgb = DARK_TXT
            bp.space_after = Pt(16)

        ftb = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4))
        fp = ftb.text_frame.paragraphs[0]
        fp.text = f"{title}  |  شريحة {idx}"
        fp.alignment = PP_ALIGN.LEFT
        fp.font.name = "Arial"
        fp.font.size = Pt(11)
        fp.font.color.rgb = SLATE

    path = "/tmp/Presentation.pptx"
    prs.save(path)
    send_file(
        cid,
        path,
        "Executive_Presentation.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        f"📽️ تم تصميم العرض التقديمي الاحترافي: *{title}*"
    )
    if os.path.exists(path):
        os.remove(path)
    del prs
    gc.collect()

def make_powerbi_kit(cid, msg):
    from docx import Document
    from docx.shared import Pt as DocPt
    send_msg(cid, "📊 *وكيل نمذجة البيانات وPower BI:* جاري هندسة نموذج البيانات ومعادلات DAX الاحترافية...")
    title = _clean_title(msg)
    prompt = (
        f"أنت خبير Power BI ومهندس ذكاء أعمال (BI Architect). للمشروع التالي: {msg}\n"
        "أعدّ وثيقة هندسية تنفيذية تشمل:\n"
        "1. هيكل الجداول المقترح (Fact & Dimension Tables) وأعمدة كل جدول.\n"
        "2. 6 معادلات DAX احترافية مكتوبة بدقة وجاهزة للنسخ المباشر داخل Power BI لحساب المؤشرات (KPIs).\n"
        "3. تصميم لوحة القيادة (Dashboard Layout) وتوزيع البطاقات والرسوم البيانية في كل صفحة."
    )
    guide = ai_ask(msg, prompt, temperature=0.2)
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = DocPt(13)
    _set_rtl(doc.add_heading(f"دليل هندسة Power BI: {title}", 0))
    _set_rtl(doc.add_paragraph(f"تاريخ الإصدار: {today_dates()}"))
    for line in guide.split("\n"):
        cl = line.strip().replace("**", "")
        if not cl:
            continue
        if cl.startswith(("#", "1.", "2.", "3.")):
            _set_rtl(doc.add_heading(cl.lstrip("# "), level=1))
        else:
            _set_rtl(doc.add_paragraph(cl))
    path = "/tmp/PowerBI_Architecture.docx"
    doc.save(path)
    send_file(cid, path, "PowerBI_Architecture.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📈 تم إعداد حزمة هندسة Power BI ومعادلات DAX: *{title}*")
    if os.path.exists(path):
        os.remove(path)
    del doc
    gc.collect()

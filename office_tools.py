import os, re, gc, pendulum
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
    from docx.shared import Pt as DocPt, RGBColor
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    send_msg(cid, "👥 *تفعيل غرفة عمليات الوثائق:* جاري هندسة التقرير المؤسسي وتنسيق الهوية البصرية...")
    title = _clean_title(msg)
    outline = ai_ask(msg, "ضع 5 محاور استراتيجية لتغطية هذا الموضوع بعمق تنفيذي. اكتب كل محور في سطر مستقل بدون مقدمات:", mode="arabic")
    sections = [re.sub(r'^[\-\*\#\d\.\s]+', '', s).strip() for s in outline.split("\n") if len(s.strip()) > 3][:5] or ["الإطار العام والرؤية", "التحليل التشغيلي", "آليات التنفيذ", "مؤشرات القياس", "التوصيات الاستراتيجية"]

    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = DocPt(13)
    doc.styles['Normal'].font.color.rgb = RGBColor(30, 41, 59)

    def _shade(cell, hex_color):
        cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'))

    def _styled_p(container, text, size=13, bold=False, color=(30, 41, 59), space_before=0, space_after=6):
        p = container.add_paragraph() if hasattr(container, 'add_paragraph') else container
        _set_rtl(p)
        p.paragraph_format.space_before = DocPt(space_before)
        p.paragraph_format.space_after = DocPt(space_after)
        p.paragraph_format.line_spacing = 1.35
        run = p.add_run(text)
        run.font.name = 'Arial'
        run.font.size = DocPt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor(*color)
        return p

    tbl_hdr = doc.add_table(rows=2, cols=1)
    tbl_hdr.autofit = False
    tbl_hdr.columns[0].width = DocPt(460)
    c0, c1 = tbl_hdr.cell(0, 0), tbl_hdr.cell(1, 0)
    _shade(c0, "0B192C")
    _shade(c1, "1E3E62")
    _styled_p(c0.paragraphs[0], title, size=22, bold=True, color=(255, 209, 102), space_before=8, space_after=8)
    _styled_p(c1.paragraphs[0], f"تاريخ الإصدار: {today_dates()}   |   إعداد: منظومة Albaraa AI OS", size=11, bold=False, color=(255, 255, 255), space_before=4, space_after=4)

    doc.add_paragraph()

    tbl_idx = doc.add_table(rows=len(sections) + 1, cols=2)
    tbl_idx.style = 'Table Grid'
    _shade(tbl_idx.cell(0, 0), "0B192C"); _shade(tbl_idx.cell(0, 1), "0B192C")
    _styled_p(tbl_idx.cell(0, 0).paragraphs[0], "المحور الاستراتيجي", size=12, bold=True, color=(255, 209, 102), space_before=3, space_after=3)
    _styled_p(tbl_idx.cell(0, 1).paragraphs[0], "الرقم", size=12, bold=True, color=(255, 209, 102), space_before=3, space_after=3)
    for i, sec in enumerate(sections, 1):
        bg = "F8FAFC" if i % 2 == 0 else "FFFFFF"
        _shade(tbl_idx.cell(i, 0), bg); _shade(tbl_idx.cell(i, 1), bg)
        _styled_p(tbl_idx.cell(i, 0).paragraphs[0], sec, size=12, bold=True, color=(15, 23, 42), space_before=2, space_after=2)
        _styled_p(tbl_idx.cell(i, 1).paragraphs[0], f"0{i}", size=12, bold=True, color=(30, 62, 98), space_before=2, space_after=2)

    for idx, sec in enumerate(sections, 1):
        _styled_p(doc, f"{idx}. {sec}", size=17, bold=True, color=(11, 25, 44), space_before=16, space_after=6)
        content = ai_ask(
            f"الموضوع الرئيسي: {title}\nالمحور الحالي: {sec}",
            "اكتب تحليلاً تنفيذياً منظماً باللغة العربية الفصحى مقسماً إلى فقرات قصيرة ونقاط عملية واضحة تبدأ بـ (▪). تجنب الحشو والتكرار:",
            mode="arabic"
        )
        for l in content.split("\n"):
            cl = l.strip().replace("**", "")
            if not cl: continue
            if cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً")):
                _styled_p(doc, cl.lstrip("# "), size=14, bold=True, color=(30, 62, 98), space_before=8, space_after=4)
            elif cl.startswith(("-", "*", "•", "▪")):
                clean_pt = re.sub(r'^[\-\*\•\▪\s]+', '', cl)
                _styled_p(doc, f"▪  {clean_pt}", size=12.5, bold=False, color=(15, 23, 42), space_before=2, space_after=4)
            else:
                _styled_p(doc, cl, size=13, bold=False, color=(30, 41, 59), space_before=2, space_after=6)

    path = "/tmp/Doc.docx"; doc.save(path)
    send_file(cid, path, "Executive_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📄 تم إصدار التقرير التنفيذي المنسّق: *{title}*")
    if os.path.exists(path): os.remove(path)
    del doc; gc.collect()

def make_excel(cid, msg):
    import openpyxl, arabic_reshaper
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from bidi.algorithm import get_display

    def _ar(txt):
        return get_display(arabic_reshaper.reshape(str(txt)), base_dir='R')
    send_msg(cid, "👥 *هندسة لوحة القيادة المؤسسية:* جاري بناء قاعدة البيانات، المؤشرات، والرسوم البيانية...")
    prompt = (
        "أنت مدير تحليلات أداء مؤسسي. أنشئ 3 أقسام مفصولة بسطر === فقط:\n"
        "1: عنوان مؤسسي رسمي للتقرير (3 إلى 6 كلمات بدون أفعال أمر).\n"
        "2: جدول بيانات من 9 صفوف (صف عناوين + 8 صفوف بيانات واقعية) بـ 6 أعمدة مفصولة بـ | فقط:\n"
        "الاسم أو البند | المسمى الوظيفي | الإدارة | المحقق الفعلي (رقم 75-115) | المستهدف (رقم 85-100) | الإجراء التطويري\n"
        "3: ملخص تنفيذي من 3 توصيات استراتيجية بدون رموز نجمية.\n"
        "التزم بالفصل بـ === بدون مقدمات."
    )
    res = ai_ask(msg, prompt, mode="fast")
    it_p = iter([p.strip() for p in res.split("===") if p.strip()])
    p1, p2, p3 = next(it_p, ""), next(it_p, ""), next(it_p, "")
    title = p1.replace('"', '').strip()[:55] if (p1 and len(p1) < 85 and "|" not in p1) else "تقرير تقييم الأداء والكفاءة المؤسسية"
    raw = p2 if "|" in p2 else res
    summary = p3 or "1. تعزيز برامج التطوير المهني للوحدات دون المستهدف.\n2. ربط الحوافز الفصلية بمؤشرات الإنجاز الفعلية.\n3. تعميم أفضل الممارسات التشغيلية."

    wb = openpyxl.Workbook()
    ws_dash = wb.active; ws_dash.title = "لوحة القيادة"; ws_dash.sheet_view.rightToLeft = True; ws_dash.sheet_view.showGridLines = False
    ws_data = wb.create_sheet("سجل البيانات والتحليل"); ws_data.sheet_view.rightToLeft = True

    _fill = lambda hx: PatternFill(start_color=hx, end_color=hx, fill_type="solid")
    f_navy, f_slate, f_white, f_zebra = _fill("0B192C"), _fill("1E3E62"), _fill("FFFFFF"), _fill("F8FAFC")
    f_green, f_blue, f_amber = _fill("DCFCE7"), _fill("DBEAFE"), _fill("FEF3C7")
    s_thin = Side(style='thin', color='CBD5E1')
    brd = Border(left=s_thin, right=s_thin, top=s_thin, bottom=s_thin)
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
    ws_data.row_dimensions[1].height = 32
    for c_i, h in enumerate(headers, 1):
        c = ws_data.cell(1, c_i, h); c.fill = f_navy; c.font = Font(color="FFD166", size=11, bold=True); c.alignment = aln_c; c.border = brd

    rows = parsed[1:]; last_r = len(rows) + 1
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
            chart_labels.append(_ar(nm[:13])); chart_act.append(ac); chart_tgt.append(tg)
        entries = [f"EMP-{100+idx}", nm, role_t, dp, ac, tg, f"{pct}%", f"{'+' if diff > 0 else ''}{diff}", eval_txt, act_plan]
        for c_i, val in enumerate(entries, 1):
            c = ws_data.cell(idx, c_i, val); c.border = brd; c.font = Font(color="0F172A", size=11, bold=(c_i in (1, 2, 7, 9))); c.alignment = aln_c if c_i in (1, 5, 6, 7, 8, 9) else aln_r
            if idx % 2 == 0: c.fill = f_zebra
            if c_i == 9: c.fill = f_green if pct >= 100 else (f_blue if pct >= 85 else f_amber)
    cnt = max(len(rows), 1); avg_pct = round(sum_pct / cnt, 1); tot_diff = round(sum_ac - sum_tg, 1)
    tot_r = last_r + 1; ws_data.row_dimensions[tot_r].height = 30
    tots = ["الإجمالي", f"{cnt} سجل", "كافة الفئات", "جميع الإدارات", round(sum_ac, 1), round(sum_tg, 1), f"{avg_pct}%", f"{'+' if tot_diff > 0 else ''}{tot_diff}", f"{pass_cnt} محقق", "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val); c.fill = f_slate; c.font = Font(color="FFFFFF", size=11, bold=True); c.alignment = aln_c; c.border = brd

    for c_i in range(1, 11): ws_data.column_dimensions[get_column_letter(c_i)].width = 25 if c_i in (2, 10) else (19 if c_i in (3, 4, 9) else 15)
    for c in range(1, 14): ws_dash.column_dimensions[get_column_letter(c)].width = 14

    ws_dash.merge_cells("B2:M3"); ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"; ws_dash["B2"].fill = f_navy; ws_dash["B2"].font = Font(color="FFD166", size=18, bold=True); ws_dash["B2"].alignment = aln_c
    ws_dash.merge_cells("B4:M4"); ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  بطاقة الأداء المتوازن والمؤشرات التشغيلية"; ws_dash["B4"].fill = f_slate; ws_dash["B4"].font = Font(color="FFFFFF", size=11); ws_dash["B4"].alignment = aln_c

    cards = [("B", "D", "إجمالي الأداء المحقق", f"{round(sum_ac, 1)}", "1E3A8A"), ("E", "G", "متوسط نسبة الإنجاز", f"{avg_pct}%", "0F766E"), ("H", "J", "الفارق عن المستهدف", f"{'+' if tot_diff > 0 else ''}{tot_diff}", "B45309"), ("K", "M", "نسبة المحققين للمعيار", f"{round((pass_cnt/cnt)*100)}%", "4338CA")]
    ws_dash.row_dimensions[6].height = 26; ws_dash.row_dimensions[7].height = 40
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6"); ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value = tk; ws_dash[f"{cs}6"].fill = _fill(hx); ws_dash[f"{cs}6"].font = Font(color="FFFFFF", size=11, bold=True); ws_dash[f"{cs}6"].alignment = aln_c
        ws_dash[f"{cs}7"].value = fk; ws_dash[f"{cs}7"].fill = f_white; ws_dash[f"{cs}7"].font = Font(color=hx, size=18, bold=True); ws_dash[f"{cs}7"].alignment = aln_c; ws_dash[f"{cs}7"].border = brd

    for r_idx in range(9, 27): ws_dash.row_dimensions[r_idx].height = 20
    chart_img = "/tmp/dash_chart.png"
    try:
        fig, ax = plt.subplots(figsize=(10.5, 4.3), dpi=130)
        fig.patch.set_facecolor('#0B192C'); ax.set_facecolor('#132743')
        x_pos = range(len(chart_labels))
        b1 = ax.bar([p - 0.18 for p in x_pos], chart_act, width=0.35, label=_ar("المحقق الفعلي"), color='#00B4D8')
        b2 = ax.bar([p + 0.18 for p in x_pos], chart_tgt, width=0.35, label=_ar("المستهدف المخطط"), color='#FFD166')
        ax.set_xticks(list(x_pos)); ax.set_xticklabels(chart_labels)
        ax.set_title(_ar("مقارنة الأداء المحقق مقابل المستهدف"), color='#FFD166', fontsize=14, fontweight='bold', pad=12)
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
    ws_dash.row_dimensions[28].height = 28
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
        'أرجع JSON فقط: {"subtitle": "وصف مختصر", "slides": [{"heading": "عنوان الشريحة", "points": ["نقطة 1", "نقطة 2", "نقطة 3", "نقطة 4"]}]}\n'
        "أنشئ 6 شرائح متنوعة باللغة العربية الفصحى."
    )
    raw = ai_ask(msg, prompt, mode="arabic").replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception:
        data = {"subtitle": "عرض تحليلي واستراتيجي شامل", "slides": [{"heading": "نظرة عامة", "points": ["تحديد الأهداف الاستراتيجية", "تحليل الوضع الراهن", "رفع كفاءة الأداء"]}]}

    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    NAVY, SLATE, GOLD, WHITE, LIGHT_BG, DARK_TXT = RGBColor(11, 25, 44), RGBColor(30, 62, 98), RGBColor(255, 209, 102), RGBColor(255, 255, 255), RGBColor(248, 250, 252), RGBColor(15, 23, 42)

    def _add_p(tf, txt, sz, clr, bold=False, align=PP_ALIGN.RIGHT, sp=0, first=False):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        p.text, p.alignment, p.font.name, p.font.size, p.font.bold, p.font.color.rgb = txt, align, "Arial", Pt(sz), bold, clr
        if sp: p.space_before = Pt(sp)

    s0 = prs.slides.add_slide(blank)
    s0.background.fill.solid(); s0.background.fill.fore_color.rgb = NAVY
    bar = s0.shapes.add_shape(1, Inches(0), Inches(6.8), Inches(13.333), Inches(0.2))
    bar.fill.solid(); bar.fill.fore_color.rgb = GOLD; bar.line.fill.background()

    tf0 = s0.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(2)).text_frame; tf0.word_wrap = True
    _add_p(tf0, title, 40, GOLD, bold=True, first=True)
    _add_p(tf0, data.get("subtitle", ""), 20, WHITE, sp=14)
    _add_p(tf0, f"تاريخ الإصدار: {today_dates()} | Albaraa AI OS", 14, RGBColor(148, 163, 184), sp=28)
    cnt = max(len(rows), 1); avg_pct = round(sum_pct / cnt, 1); tot_diff = round(sum_ac - sum_tg, 1)
    tot_r = last_r + 1; ws_data.row_dimensions[tot_r].height = 30
    tots = ["الإجمالي", f"{cnt} سجل", "كافة الفئات", "جميع الإدارات", round(sum_ac, 1), round(sum_tg, 1), f"{avg_pct}%", f"{'+' if tot_diff > 0 else ''}{tot_diff}", f"{pass_cnt} محقق", "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val); c.fill = f_slate; c.font = Font(color="FFFFFF", size=11, bold=True); c.alignment = aln_c; c.border = brd

    for c_i in range(1, 11): ws_data.column_dimensions[get_column_letter(c_i)].width = 25 if c_i in (2, 10) else (19 if c_i in (3, 4, 9) else 15)
    for c in range(1, 14): ws_dash.column_dimensions[get_column_letter(c)].width = 14

    ws_dash.merge_cells("B2:M3"); ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"; ws_dash["B2"].fill = f_navy; ws_dash["B2"].font = Font(color="FFD166", size=18, bold=True); ws_dash["B2"].alignment = aln_c
    ws_dash.merge_cells("B4:M4"); ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  بطاقة الأداء المتوازن والمؤشرات التشغيلية"; ws_dash["B4"].fill = f_slate; ws_dash["B4"].font = Font(color="FFFFFF", size=11); ws_dash["B4"].alignment = aln_c
    for idx, sl in enumerate(data.get("slides", [])[:8], 1):
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid(); slide.background.fill.fore_color.rgb = LIGHT_BG
        hdr = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
        hdr.fill.solid(); hdr.fill.fore_color.rgb = NAVY; hdr.line.fill.background()

        accent = slide.shapes.add_shape(1, Inches(0), Inches(1.2), Inches(13.333), Inches(0.08))
        accent.fill.solid(); accent.fill.fore_color.rgb = GOLD; accent.line.fill.background()

        htf = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.7)).text_frame
        _add_p(htf, f"{idx}. {sl.get('heading', '')}", 26, GOLD, bold=True, first=True)

        btf = slide.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.8)).text_frame; btf.word_wrap = True
        for p_i, pt_text in enumerate(sl.get("points", [])):
            _add_p(btf, f"▪ {pt_text}", 20, DARK_TXT, first=(p_i == 0))
            btf.paragraphs[p_i].space_after = Pt(16)

        ftf = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4)).text_frame
        _add_p(ftf, f"{title}  |  شريحة {idx}", 11, SLATE, align=PP_ALIGN.LEFT, first=True)

    path = "/tmp/Presentation.pptx"; prs.save(path)
    send_file(cid, path, "Executive_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", f"📽️ تم تصميم العرض التقديمي الاحترافي: *{title}*")
    if os.path.exists(path): os.remove(path)
    del prs; gc.collect()

def make_powerbi_kit(cid, msg):
    from docx import Document
    from docx.shared import Pt as DocPt, RGBColor
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    send_msg(cid, "📊 *وكيل نمذجة البيانات وPower BI:* جاري هندسة نموذج البيانات ومعادلات DAX الاحترافية...")
    title = _clean_title(msg)
    prompt = (
        f"أنت خبير Power BI ومهندس ذكاء أعمال (BI Architect). للمشروع التالي: {msg}\n"
        "أعدّ وثيقة هندسية تنفيذية تشمل:\n"
        "1. هيكل الجداول المقترح (Fact & Dimension Tables) وأعمدة كل جدول.\n"
        "2. 6 معادلات DAX احترافية مكتوبة بدقة وجاهزة للنسخ المباشر داخل Power BI لحساب المؤشرات (KPIs).\n"
        "3. تصميم لوحة القيادة (Dashboard Layout) وتوزيع البطاقات والرسوم البيانية في كل صفحة."
    )
    guide = ai_ask(msg, prompt, temperature=0.2, mode="arabic")

    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = DocPt(13)

    tbl = doc.add_table(rows=1, cols=1)
    cell = tbl.cell(0, 0)
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="0B192C"/>'))
    p0 = cell.paragraphs[0]
    _set_rtl(p0)
    r0 = p0.add_run(f"دليل هندسة Power BI: {title}\n")
    r0.font.name = 'Arial'; r0.font.size = DocPt(18); r0.font.bold = True; r0.font.color.rgb = RGBColor(255, 209, 102)
    r1 = p0.add_run(f"تاريخ الإصدار: {today_dates()}  |  Albaraa AI OS")
    r1.font.name = 'Arial'; r1.font.size = DocPt(11); r1.font.color.rgb = RGBColor(255, 255, 255)

    for line in guide.split("\n"):
        cl = line.strip().replace("**", "")
        if not cl: continue
        p = doc.add_paragraph()
        _set_rtl(p)
        run = p.add_run(cl.lstrip("# "))
        run.font.name = 'Arial'
        if cl.startswith(("#", "1.", "2.", "3.")):
            run.font.size = DocPt(15); run.font.bold = True; run.font.color.rgb = RGBColor(11, 25, 44)
        else:
            run.font.size = DocPt(12.5); run.font.color.rgb = RGBColor(30, 41, 59)

    path = "/tmp/PowerBI_Architecture.docx"; doc.save(path)
    send_file(cid, path, "PowerBI_Architecture.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📈 تم إعداد حزمة هندسة Power BI ومعادلات DAX: *{title}*")
    if os.path.exists(path): os.remove(path)
    del doc; gc.collect()

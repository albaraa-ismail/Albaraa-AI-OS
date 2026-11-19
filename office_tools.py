import os, gc, pendulum
from hijridate import Gregorian
from core_ai import sb, ai_ask, send_msg, send_file

def today_dates():
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ - {now.format('YYYY/MM/DD')}م"

def _clean_title(msg):
    t = ai_ask(msg, "حول الطلب إلى عنوان تقرير مؤسسي رسمي من 3 إلى 6 كلمات بدون أفعال أمر (مثل عطني، صمم، اكتب). العنوان فقط:").replace('"', '').strip()[:60]
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
    outline = ai_ask(msg, "ضع 5 محاور رئيسية لتغطية هذا الموضوع بعمق تنفيذي ومؤسسي. اكتب كل محور في سطر مستقل بدون مقدمات:")
    sections = []
    for s in outline.split("\n"):
        cs = s.strip().lstrip("-*#1234567890. ")
        if len(cs) > 3 and len(sections) < 5: sections.append(cs)
    if not sections:
        sections = ["الملخص التنفيذي والإطار العام", "التحليل والمنهجية", "التطبيقات التشغيلية", "مؤشرات الأداء والقياس", "التوصيات وخطة العمل"]

    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'; doc.styles['Normal'].font.size = DocPt(14)
    _set_rtl(doc.add_heading(title, 0))
    _set_rtl(doc.add_paragraph(f"تاريخ الإصدار: {today_dates()}"))

    for sec in sections:
        _set_rtl(doc.add_heading(sec, level=1))
        content = ai_ask(f"الموضوع: {title}\nالمحور: {sec}", "اكتب محتوى تنفيذياً غزيراً ومفصلاً باللغة العربية الفصحى مقسماً إلى فقرات وعناوين فرعية:")
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
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import arabic_reshaper
    from bidi.algorithm import get_display

    send_msg(cid, "👥 *هندسة لوحة القيادة المؤسسية:* جاري بناء قاعدة بيانات الموظفين، مؤشرات الأداء، والرسوم البيانية...")
    prompt = (
        "أنت مدير تحليلات موارد بشرية وأداء مؤسسي. أنشئ 3 أقسام مفصولة بسطر === فقط:\n"
        "1: عنوان مؤسسي رسمي للتقرير (3 إلى 6 كلمات بدون أفعال أمر مثل عطني، صمم، اكتب).\n"
        "2: جدول بيانات من 13 صفاً (صف عناوين + 12 صف بيانات واقعية شاملة) بـ 6 أعمدة مفصولة بـ | فقط:\n"
        "الاسم أو البند | المسمى الوظيفي / التصنيف | الإدارة | المحقق الفعلي (رقم 72-115) | المستهدف (رقم 85-100) | الإجراء التطويري المقترح\n"
        "3: ملخص تنفيذي من 3 توصيات استراتيجية للإدارة والموظفين.\n"
        "التزم بالفصل بـ === بدون أي مقدمات."
    )
    res = ai_ask(msg, prompt)

    it_p = iter([p.strip() for p in res.split("===") if p.strip()])
    p1, p2, p3 = next(it_p, ""), next(it_p, ""), next(it_p, "")
    title = p1.replace('"', '').strip()[:55] if (p1 and len(p1) < 85 and "|" not in p1) else "تقرير تقييم الأداء والكفاءة المؤسسية"
    raw = p2 if "|" in p2 else res
    summary = p3 or "1. تعزيز برامج التطوير المهني للوحدات دون المستهدف.\n2. ربط الحوافز الفصلية بمؤشرات الإنجاز الفعلية.\n3. تعميم أفضل الممارسات التشغيلية من الفرق المتفوقة."

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
        parsed = [
            ["الاسم", "المسمى", "الإدارة", "المحقق", "المستهدف", "الإجراء"],
            ["سارة القحطاني", "أخصائي أول", "الموارد البشرية", 98, 90, "ترشيح للقيادة التنفيذية"],
            ["عبدالله العتيبي", "مهندس مشاريع", "العمليات", 92, 95, "تحسين جدولة التسليم"],
            ["نورة الشمري", "محلل مالي", "المالية", 104, 100, "تعميم نموذج العمل"]
        ]

    headers = ["الرقم الوظيفي", "الاسم / البند", "المسمى / التصنيف", "الإدارة", "المحقق الفعلي", "المستهدف", "الإنجاز %", "الفارق", "التقييم المعتمد", "خطة التطوير والإجراء"]
    ws_data.row_dimensions.height = 32
    for c_i, h in enumerate(headers, 1):
        c = ws_data.cell(1, c_i, h); c.fill = f_navy; c.font = Font(color="FFD166", size=11, bold=True); c.alignment = aln_c; c.border = brd

    it_rows = iter(parsed); next(it_rows, None)
    rows = list(it_rows); last_r = len(rows) + 1
    chart_labels, chart_act, chart_tgt = [], [], []
    sum_ac, sum_tg, sum_pct, max_ac, pass_cnt = 0, 0, 0.0, 0, 0

    for idx, r in enumerate(rows, 2):
        ws_data.row_dimensions[idx].height = 26
        it_c = iter(r)
        nm = str(next(it_c, "موظف"))
        role_t = str(next(it_c, "أخصائي"))
        dp = str(next(it_c, "العمليات"))
        raw_ac = next(it_c, 88)
        raw_tg = next(it_c, 90)
        act_plan = str(next(it_c, "استمرار المتابعة الدورية"))

        ac = raw_ac if isinstance(raw_ac, (int, float)) else 88
        tg = raw_tg if isinstance(raw_tg, (int, float)) else 90
        pct = round((ac / max(tg, 1)) * 100, 1)
        diff = round(ac - tg, 1)
        eval_txt = "متفوق 🌟" if pct >= 100 else ("جيد جداً ✅" if pct >= 85 else "يحتاج تطوير ⚠️")
        emp_id = f"EMP-{100 + idx}"

        sum_ac += ac; sum_tg += tg; sum_pct += pct
        if ac > max_ac: max_ac = ac
        if pct >= 85: pass_cnt += 1

        if len(chart_labels) < 7:
            chart_labels.append(get_display(arabic_reshaper.reshape(nm[:13])))
            chart_act.append(ac)
            chart_tgt.append(tg)

        entries = [emp_id, nm, role_t, dp, ac, tg, f"{pct}%", f"{'+' if diff > 0 else ''}{diff}", eval_txt, act_plan]
        for c_i, val in enumerate(entries, 1):
            c = ws_data.cell(idx, c_i, val); c.border = brd
            c.font = Font(color="0F172A", size=11, bold=(c_i in (1, 2, 7, 9)))
            c.alignment = aln_c if c_i in (1, 5, 6, 7, 8, 9) else aln_r
            if idx % 2 == 0: c.fill = f_zebra
            if c_i == 9: c.fill = f_green if pct >= 100 else (f_blue if pct >= 85 else f_amber)

    cnt = max(len(rows), 1)
    avg_pct = round(sum_pct / cnt, 1)
    tot_diff = round(sum_ac - sum_tg, 1)

    tot_r = last_r + 1; ws_data.row_dimensions.height = 30
    tots = ["الإجمالي", f"{cnt} سجل", "كافة الفئات", "جميع الإدارات", round(sum_ac, 1), round(sum_tg, 1), f"{avg_pct}%", f"{'+' if tot_diff > 0 else ''}{tot_diff}", f"{pass_cnt} محقق", "مؤشر الأداء العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val); c.fill = f_slate; c.font = Font(color="FFFFFF", size=11, bold=True); c.alignment = aln_c; c.border = brd

    widths = [14, 22, 20, 18, 15, 14, 14, 13, 18, 28]
    for c_i, w in enumerate(widths, 1): ws_data.column_dimensions[get_column_letter(c_i)].width = w
    for c in range(1, 14): ws_dash.column_dimensions[get_column_letter(c)].width = 14

    ws_dash.merge_cells("B2:M3"); ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"; ws_dash["B2"].fill = f_navy; ws_dash["B2"].font = Font(color="FFD166", size=18, bold=True); ws_dash["B2"].alignment = aln_c
    ws_dash.merge_cells("B4:M4"); ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  بطاقة الأداء المتوازن والمؤشرات التشغيلية"; ws_dash["B4"].fill = f_slate; ws_dash["B4"].font = Font(color="FFFFFF", size=11); ws_dash["B4"].alignment = aln_c

    cards = [
        ("B", "D", "إجمالي الأداء المحقق", f"{round(sum_ac, 1)}", "1E3A8A"),
        ("E", "G", "متوسط نسبة الإنجاز", f"{avg_pct}%", "0F766E"),
        ("H", "J", "الفارق عن المستهدف", f"{'+' if tot_diff > 0 else ''}{tot_diff}", "B45309"),
        ("K", "M", "نسبة المحققين للمعيار", f"{round((pass_cnt/cnt)*100)}%", "4338CA"),
    ]
    ws_dash.row_dimensions.height = 26; ws_dash.row_dimensions.height = 40
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6"); ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value = tk; ws_dash[f"{cs}6"].fill = PatternFill(start_color=hx, end_color=hx, fill_type="solid"); ws_dash[f"{cs}6"].font = Font(color="FFFFFF", size=11, bold=True); ws_dash[f"{cs}6"].alignment = aln_c
        ws_dash[f"{cs}7"].value = fk; ws_dash[f"{cs}7"].fill = f_white; ws_dash[f"{cs}7"].font = Font(color=hx, size=18, bold=True); ws_dash[f"{cs}7"].alignment = aln_c; ws_dash[f"{cs}7"].border = brd

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
            img_xl = XLImage(chart_img); img_xl.width = 840; img_xl.height = 345
            ws_dash.add_image(img_xl, "B9")
    except Exception as e:
        print("Chart Img Err:", e, flush=True)

    ws_dash.merge_cells("B27:M27"); ws_dash["B27"] = "💡 القراءة التحليلية والتوصيات التنفيذية للإدارة"; ws_dash["B27"].fill = f_navy; ws_dash["B27"].font = Font(color="FFD166", size=12, bold=True); ws_dash["B27"].alignment = aln_r

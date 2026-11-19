import os, gc, pendulum
from hijridate import Gregorian
from core_ai import sb, ai_ask, send_msg, send_file

def today_dates():
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ - {now.format('YYYY/MM/DD')}م"

def _clean_title(msg):
    t = ai_ask(msg, "حول الطلب إلى عنوان تقرير تنفيذي فخم من 3 إلى 6 كلمات بدون أفعال أمر (مثل عطني، صمم، اكتب). العنوان فقط:").replace('"', '').strip()[:60]
    if "تعذر" in t or len(t) < 4:
        for w in ("عطني", "أعطني", "اعطني", "صمم", "اكتب", "سوي", "اعمل", "أريد", "ابي", "أبي", "لوحة تحكم"):
            msg = msg.replace(w, "")
        t = msg.strip()[:55] or "لوحة المؤشرات التنفيذية"
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
    outline = ai_ask(msg, "ضع 5 محاور رئيسية لتغطية هذا الموضوع بعمق تنفيذي. اكتب كل محور في سطر مستقل بدون مقدمات:")
    sections = []
    for s in outline.split("\n"):
        cs = s.strip().lstrip("-*#1234567890. ")
        if len(cs) > 3 and len(sections) < 5: sections.append(cs)
    if not sections:
        sections = ["الإطار العام", "التحليل والمنهجية", "التطبيقات العملية", "مؤشرات القياس", "التوصيات"]

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

    send_msg(cid, "👥 *هندسة لوحة القيادة التفاعلية:* جاري بناء قاعدة البيانات، المعادلات الحية، والرسوم البيانية...")
    prompt = (
        "أنت مهندس بيانات خبير. أنشئ 3 أقسام مفصولة بسطر === فقط:\n"
        "1: عنوان رسمي فخم للتقرير (3 إلى 6 كلمات بدون أفعال أمر مثل عطني، صمم، اكتب).\n"
        "2: جدول بيانات من 13 صفاً (صف عناوين + 12 صف بيانات واقعية) بـ 5 أعمدة مفصولة بـ | فقط:\n"
        "البند أو الموظف | الإدارة | المحقق الفعلي (رقم 70-115) | المستهدف (رقم 85-105) | ملاحظة موجزة\n"
        "3: ملخص تنفيذي من 3 توصيات عملية قصيرة ومباشرة.\n"
        "التزم بالفصل بـ === بدون مقدمات."
    )
    res = ai_ask(msg, prompt)

    it_p = iter([p.strip() for p in res.split("===") if p.strip()])
    p1, p2, p3 = next(it_p, ""), next(it_p, ""), next(it_p, "")
    title = p1.replace('"', '').strip()[:55] if (p1 and len(p1) < 85 and "|" not in p1) else "تقرير مؤشرات الأداء الاستراتيجية"
    raw = p2 if "|" in p2 else res
    summary = p3 or "مؤشرات الأداء تظهر كفاءة تشغيلية عالية مع فرص لتحسين الإنجاز في الوحدات ذات الفارق السلبي."

    wb = openpyxl.Workbook()
    ws_dash = wb.active; ws_dash.title = "لوحة القيادة"; ws_dash.sheet_view.rightToLeft = True; ws_dash.sheet_view.showGridLines = False
    ws_data = wb.create_sheet("البيانات والتحليل"); ws_data.sheet_view.rightToLeft = True

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
                if v and len(vals) < 5:
                    try: v = float(v) if "." in v else int(v)
                    except ValueError: pass
                    vals.append(v)
            if len(vals) >= 4: parsed.append(vals)

    if len(parsed) < 2:
        parsed = [["البند", "القسم", "المحقق", "المستهدف", "ملاحظة"], ["الكفاءة التشغيلية", "العمليات", 95, 90, "تجاوز المستهدف"], ["جودة المخرجات", "الجودة", 89, 92, "أداء مستقر"], ["سرعة الإنجاز", "التطوير", 98, 85, "أعلى معدل إنجاز"]]

    headers = ["البند / الموظف", "الإدارة", "المحقق الفعلي", "المستهدف", "الإنجاز %", "الفارق", "التقييم الآلي", "ملاحظات المتابعة"]
    ws_data.row_dimensions.height = 30
    for c_i, h in enumerate(headers, 1):
        c = ws_data.cell(1, c_i, h); c.fill = f_navy; c.font = Font(color="FFD166", size=11, bold=True); c.alignment = aln_c; c.border = brd

    it_rows = iter(parsed); next(it_rows, None)
    rows = list(it_rows); last_r = len(rows) + 1
    chart_labels, chart_vals = [], []

    for idx, r in enumerate(rows, 2):
        ws_data.row_dimensions[idx].height = 24
        it_c = iter(r)
        nm, dp, ac, tg, nt = str(next(it_c, "بند")), str(next(it_c, "عام")), next(it_c, 85), next(it_c, 90), str(next(it_c, "مستمر"))
        ac = ac if isinstance(ac, (int, float)) else 85
        tg = tg if isinstance(tg, (int, float)) else 90
        pct = round((ac / max(tg, 1)) * 100, 1)

        if len(chart_labels) < 8:
            chart_labels.append(get_display(arabic_reshaper.reshape(nm[:14])))
            chart_vals.append(ac)

        entries = [nm, dp, ac, tg, f"=ROUND((C{idx}/MAX(D{idx},1))*100,1)", f"=C{idx}-D{idx}", f'=IF(E{idx}>=100,"متفوق 🌟",IF(E{idx}>=85,"جيد جداً ✅","يحتاج دعم ⚠️"))', nt]
        for c_i, val in enumerate(entries, 1):
            c = ws_data.cell(idx, c_i, val); c.border = brd; c.font = Font(color="0F172A", size=11, bold=(c_i in (1, 5, 7))); c.alignment = aln_c if c_i in (3,4,5,6,7) else aln_r
            if idx % 2 == 0: c.fill = f_zebra
            if c_i == 7: c.fill = f_green if pct >= 100 else (f_blue if pct >= 85 else f_amber)

    tot_r = last_r + 1; ws_data.row_dimensions.height = 28
    tots = ["الإجمالي / المتوسط", f'=COUNTA(A2:A{last_r})&" سجل"', f"=SUM(C2:C{last_r})", f"=SUM(D2:D{last_r})", f"=ROUND(AVERAGE(E2:E{last_r}),1)", f"=SUM(F2:F{last_r})", f'=COUNTIF(E2:E{last_r},">=85")&" محقق"', "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val); c.fill = f_slate; c.font = Font(color="FFFFFF", size=11, bold=True); c.alignment = aln_c; c.border = brd

    for c_i in range(1, 9): ws_data.column_dimensions[get_column_letter(c_i)].width = 23 if c_i in (1, 8) else 16
    for c in range(1, 14): ws_dash.column_dimensions[get_column_letter(c)].width = 13

    ws_dash.merge_cells("B2:M3"); ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"; ws_dash["B2"].fill = f_navy; ws_dash["B2"].font = Font(color="FFD166", size=18, bold=True); ws_dash["B2"].alignment = aln_c
    ws_dash.merge_cells("B4:M4"); ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  نظام المتابعة والتحليل التنفيذي"; ws_dash["B4"].fill = f_slate; ws_dash["B4"].font = Font(color="FFFFFF", size=11); ws_dash["B4"].alignment = aln_c

    cards = [
        ("B", "D", "إجمالي المحقق الفعلي", f"='البيانات والتحليل'!C{tot_r}", "1E3A8A"),
        ("E", "G", "متوسط نسبة الإنجاز %", f"='البيانات والتحليل'!E{tot_r}", "0F766E"),
        ("H", "J", "صافي الفارق عن المستهدف", f"='البيانات والتحليل'!F{tot_r}", "B45309"),
        ("K", "M", "أعلى قيمة مسجلة", f"=MAX('البيانات والتحليل'!C2:C{last_r})", "4338CA"),
    ]
    ws_dash.row_dimensions.height = 24; ws_dash.row_dimensions.height = 38
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6"); ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value = tk; ws_dash[f"{cs}6"].fill = PatternFill(start_color=hx, end_color=hx, fill_type="solid"); ws_dash[f"{cs}6"].font = Font(color="FFFFFF", size=11, bold=True); ws_dash[f"{cs}6"].alignment = aln_c
        ws_dash[f"{cs}7"].value = fk; ws_dash[f"{cs}7"].fill = f_white; ws_dash[f"{cs}7"].font = Font(color=hx, size=18, bold=True); ws_dash[f"{cs}7"].alignment = aln_c; ws_dash[f"{cs}7"].border = brd

    chart_img = "/tmp/dash_chart.png"
    try:
        fig, ax = plt.subplots(figsize=(9.5, 4.2), dpi=130)
        fig.patch.set_facecolor('#0B192C'); ax.set_facecolor('#132743')
        bars = ax.bar(chart_labels, chart_vals, color=['#00B4D8', '#0096C7', '#48CAE4', '#FFD166', '#06D6A0', '#118AB2', '#EF476F', '#8338EC'], width=0.5)
        ax.set_title(get_display(arabic_reshaper.reshape("تحليل مؤشرات الأداء الفعلي")), color='#FFD166', fontsize=14, fontweight='bold', pad=12)
        ax.tick_params(colors='white', labelsize=10)
        for sp in ax.spines.values(): sp.set_visible(False)
        for b in bars:
            yv = b.get_height()
            ax.text(b.get_x() + b.get_width()/2, yv + 1, str(yv), ha='center', va='bottom', color='white', fontsize=10, fontweight='bold')
        plt.tight_layout(); plt.savefig(chart_img, facecolor='#0B192C'); plt.close(fig)
        if os.path.exists(chart_img):
            img_xl = XLImage(chart_img); img_xl.width = 760; img_xl.height = 335
            ws_dash.add_image(img_xl, "B9")
    except Exception as e:
        print("Chart Img Err:", e, flush=True)

    ws_dash.merge_cells("B27:M27"); ws_dash["B27"] = "💡 القراءة التحليلية والتوصيات التنفيذية"; ws_dash["B27"].fill = f_navy; ws_dash["B27"].font = Font(color="FFD166", size=12, bold=True); ws_dash["B27"].alignment = aln_r
    ws_dash.merge_cells("B28:M33"); ws_dash["B28"] = summary.replace("**", ""); ws_dash["B28"].fill = f_white; ws_dash["B28"].font = Font(color="1E293B", size=11); ws_dash["B28"].alignment = Alignment(horizontal="right", vertical="top", wrap_text=True); ws_dash["B28"].border = brd

    path = "/tmp/Executive_Dashboard.xlsx"; wb.save(path)
    send_file(cid, path, "Executive_Dashboard.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"📊 تم إعداد لوحة القيادة التفاعلية: *{title}*\n✨ تشمل واجهة قيادة بصرية + ورقة بيانات بمعادلات تلقائية وتقييم آلي.")
    for f in (path, chart_img):
        if os.path.exists(f): os.remove(f)
    del wb; gc.collect()

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
    sections = [s.strip().lstrip("-*#1234567890. ") for s in outline.split("\n") if len(s.strip()) > 3][:5] or ["الإطار العام", "التحليل والمنهجية", "التطبيقات العملية", "مؤشرات القياس", "التوصيات"]

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
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference

    send_msg(cid, "👥 *هندسة لوحة القيادة التفاعلية:* جاري بناء قاعدة البيانات، المعادلات الحية، والرسوم البيانية...")
    prompt = (
        "أنت مهندس بيانات خبير. أنشئ 3 أقسام مفصولة بسطر === فقط:\n"
        "1: عنوان رسمي فخم للتقرير (3 إلى 6 كلمات بدون أفعال أمر).\n"
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

    fill = lambda c: PatternFill(start_color=c, end_color=c, fill_type="solid")
    fnt = lambda c="0F172A", sz=11, b=False: Font(color=c, size=sz, bold=b)
    aln = lambda h="center", v="center", w=True: Alignment(horizontal=h, vertical=v, wrap_text=w)
    brd = Border(left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'), top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1'))

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
        c = ws_data.cell(1, c_i, h); c.fill = fill("0B192C"); c.font = fnt("FFD166", 11, True); c.alignment = aln(); c.border = brd

    it_rows = iter(parsed); next(it_rows, None)
    rows = list(it_rows); last_r = len(rows) + 1

    for idx, r in enumerate(rows, 2):
        ws_data.row_dimensions[idx].height = 24
        it_c = iter(r)
        nm, dp, ac, tg, nt = str(next(it_c, "بند")), str(next(it_c, "عام")), next(it_c, 85), next(it_c, 90), str(next(it_c, "مستمر"))
        ac = ac if isinstance(ac, (int, float)) else 85
        tg = tg if isinstance(tg, (int, float)) else 90
        pct = round((ac / max(tg, 1)) * 100, 1)

        entries = [nm, dp, ac, tg, f"=ROUND((C{idx}/MAX(D{idx},1))*100,1)", f"=C{idx}-D{idx}", f'=IF(E{idx}>=100,"متفوق 🌟",IF(E{idx}>=85,"جيد جداً ✅","يحتاج دعم ⚠️"))', nt]
        for c_i, val in enumerate(entries, 1):
            c = ws_data.cell(idx, c_i, val); c.border = brd; c.font = fnt(b=(c_i in (1, 5, 7))); c.alignment = aln("center" if c_i in (3,4,5,6,7) else "right")
            if idx % 2 == 0: c.fill = fill("F8FAFC")
            if c_i == 7: c.fill = fill("DCFCE7" if pct >= 100 else ("DBEAFE" if pct >= 85 else "FEF3C7"))

    tot_r = last_r + 1; ws_data.row_dimensions[tot_r].height = 28
    tots = ["الإجمالي / المتوسط", f'=COUNTA(A2:A{last_r})&" سجل"', f"=SUM(C2:C{last_r})", f"=SUM(D2:D{last_r})", f"=ROUND(AVERAGE(E2:E{last_r}),1)", f"=SUM(F2:F{last_r})", f'=COUNTIF(E2:E{last_r},">=85")&" محقق"', "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val); c.fill = fill("1E3E62"); c.font = fnt("FFFFFF", 11, True); c.alignment = aln(); c.border = brd

    for c_i in range(1, 9): ws_data.column_dimensions[get_column_letter(c_i)].width = 23 if c_i in (1, 8) else 16

    for r in range(1, 36):
        ws_dash.row_dimensions[r].height = 22
        for c in range(1, 14): ws_dash.cell(r, c).fill = fill("F1F5F9")
    for c in range(1, 14): ws_dash.column_dimensions[get_column_letter(c)].width = 13

    ws_dash.merge_cells("B2:M3"); ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"; ws_dash["B2"].fill = fill("0B192C"); ws_dash["B2"].font = fnt("FFD166", 18, True); ws_dash["B2"].alignment = aln()
    ws_dash.merge_cells("B4:M4"); ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  نظام المتابعة والتحليل التنفيذي"; ws_dash["B4"].fill = fill("1E3E62"); ws_dash["B4"].font = fnt("FFFFFF", 11); ws_dash["B4"].alignment = aln()

    cards = [
        ("B", "D", "إجمالي المحقق الفعلي", f"='البيانات والتحليل'!C{tot_r}", "1E3A8A"),
        ("E", "G", "متوسط نسبة الإنجاز %", f"='البيانات والتحليل'!E{tot_r}", "0F766E"),
        ("H", "J", "صافي الفارق عن المستهدف", f"='البيانات والتحليل'!F{tot_r}", "B45309"),
        ("K", "M", "أعلى قيمة مسجلة", f"=MAX('البيانات والتحليل'!C2:C{last_r})", "4338CA"),
    ]
    ws_dash.row_dimensions.height = 24; ws_dash.row_dimensions.height = 38
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6"); ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value = tk; ws_dash[f"{cs}6"].fill = fill(hx); ws_dash[f"{cs}6"].font = fnt("FFFFFF", 11, True); ws_dash[f"{cs}6"].alignment = aln()
        ws_dash[f"{cs}7"].value = fk; ws_dash[f"{cs}7"].fill = fill("FFFFFF"); ws_dash[f"{cs}7"].font = fnt(hx, 18, True); ws_dash[f"{cs}7"].alignment = aln()

    d_ref = Reference(ws_data, min_col=3, max_col=4, min_row=1, max_row=last_r)
    c_ref = Reference(ws_data, min_col=1, min_row=2, max_row=last_r)

    bc = BarChart(); bc.type = "col"; bc.style = 10; bc.title = "مقارنة المحقق مقابل المستهدف"; bc.width = 16; bc.height = 11
    bc.add_data(d_ref, titles_from_data=True); bc.set_categories(c_ref); ws_dash.add_chart(bc, "B9")


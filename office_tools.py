import os, gc, pendulum
from hijridate import Gregorian
from core_ai import sb, ai_ask, send_msg, send_file

def today_dates():
    now = pendulum.now("Asia/Riyadh")
    hijri = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{hijri.day}/{hijri.month}/{hijri.year}هـ - {now.format('YYYY/MM/DD')}م"

def _clean_title(msg):
    t = ai_ask(msg, "حول هذا الطلب إلى عنوان تقرير تنفيذي فخم من 3 إلى 6 كلمات بدون أي أفعال أمر مثل (عطني، صمم، اكتب، سوي، ابي). اكتب العنوان فقط بدون علامات تنصيص:").replace('"', '').strip()[:65]
    if "تعذر" in t or len(t) < 4:
        for w in ("عطني", "أعطني", "اعطني", "صمم", "اكتب", "سوي", "اعمل", "أريد", "ابي", "أبي", "لوحة تحكم"):
            msg = msg.replace(w, "")
        t = msg.strip()[:60] or "منظومة مؤشرات الأداء الاستراتيجية"
    return t

def _set_rtl(p):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = p._p.get_or_add_pPr()
    pPr.append(OxmlElement('w:bidi'))

def make_kpi(cid):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(["رقم العملية", "المستخدم", "القسم", "زمن التنفيذ(ث)", "الوقت الموفر(د)", "مؤشر التطور%", "المخرج"])
    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50"):
        ws.append([i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")])
    path = "/tmp/KPI.xlsx"
    wb.save(path)
    send_file(cid, path, "Performance_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"📊 تقرير قياس الأداء ({today_dates()})")
    if os.path.exists(path): os.remove(path)
    del wb; gc.collect()

def make_word(cid, msg):
    from docx import Document
    from docx.shared import Pt as DocPt
    send_msg(cid, "👥 *تفعيل غرفة عمليات الوثائق:*\n1️⃣ وكيل التخطيط يبني الهيكل...\n2️⃣ وكيل التحرير يصيغ المحاور...\n3️⃣ وكيل التدقيق يراجع الجودة...")
    formal_title = _clean_title(msg)
    outline = ai_ask(msg, "ضع خطة هيكلية احترافية من 5 محاور رئيسية لتغطية هذا الموضوع بعمق أكاديمي وتنفيذي. اكتب كل محور في سطر مستقل بدون مقدمات:")
    sections = [s.strip().lstrip("-*#1234567890. ") for s in outline.split("\n") if len(s.strip()) > 3][:5]
    if not sections:
        sections = ["المقدمة والإطار العام", "التحليل والمنهجية", "التطبيقات العملية", "مؤشرات الأداء والقياس", "النتائج والتوصيات"]

    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = DocPt(14)

    title_p = doc.add_heading(formal_title, 0); _set_rtl(title_p)
    date_p = doc.add_paragraph(f"تاريخ الإصدار: {today_dates()}"); _set_rtl(date_p)

    for sec in sections:
        h = doc.add_heading(sec, level=1); _set_rtl(h)
        content = ai_ask(f"الموضوع: {formal_title}\nالمحور المطلوب: {sec}", "اكتب محتوى علمياً وتنفيذياً غزيراً ومفصلاً ومنقحاً باللغة العربية الفصحى مقسماً إلى فقرات وعناوين فرعية:")
        for l in content.split("\n"):
            cl = l.strip().replace("**", "")
            if not cl: continue
            if cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً")):
                sh = doc.add_heading(cl.lstrip("# "), level=2); _set_rtl(sh)
            else:
                p = doc.add_paragraph(cl); _set_rtl(p)

    path = "/tmp/Doc.docx"
    doc.save(path)
    send_file(cid, path, "Executive_Document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📄 تم إعداد المستند الاحترافي: *{formal_title}*\n💡 هل تود تحويل هذا المستند إلى عرض تقديمي أو ملخص تنفيذي؟")
    if os.path.exists(path): os.remove(path)
    del doc; gc.collect()

def make_excel(cid, msg):
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, PieChart, Reference
    from openpyxl.formatting.rule import DataBarRule

    send_msg(cid, "👥 *هندسة لوحة القيادة التفاعلية:*\n1️⃣ بناء قاعدة البيانات والمعادلات الحية...\n2️⃣ تصميم واجهة المؤشرات والرسوم البيانية...")
    formal_title = _clean_title(msg)

    prompt_data = (
        "أنشئ بيانات واقعية غنية ومفصلة من 16 صفاً (صف عناوين + 15 صف بيانات حقيقية) بـ 5 أعمدة بالضبط:\n"
        "العمود 1: الاسم أو البند أو المبادرة (نص واقعي)\n"
        "العمود 2: الإدارة أو التصنيف (نص)\n"
        "العمود 3: المحقق الفعلي (رقم صحيح واقعي بين 65 و 120)\n"
        "العمود 4: المستهدف المخطط (رقم صحيح واقعي بين 80 و 110)\n"
        "العمود 5: ملاحظة تنفيذية موجزة (جملة قصيرة من 3 كلمات)\n"
        "افصل بين الأعمدة بعلامة | فقط بدون مقدمات أو خطوط فصل."
    )
    raw = ai_ask(msg, prompt_data)

    summary_txt = ai_ask(
        f"الموضوع: {formal_title}\nالبيانات:\n{raw[:1200]}",
        "اكتب ملخصاً تنفيذياً مركزاً من 3 نقاط قصيرة ومباشرة يبرز أهم الاستنتاجات والتوصيات بناءً على هذه البيانات (بدون مقدمات):"
    )

    wb = openpyxl.Workbook()

    # ==========================================
    # الورقة 1: لوحة القيادة البصرية (Dashboard)
    # ==========================================
    ws_dash = wb.active
    ws_dash.title = "لوحة القيادة"
    ws_dash.sheet_view.rightToLeft = True
    ws_dash.sheet_view.showGridLines = False

    # ==========================================
    # الورقة 2: البيانات التفصيلية والمعادلات
    # ==========================================
    ws_data = wb.create_sheet(title="البيانات والتحليل")
    ws_data.sheet_view.rightToLeft = True
    ws_data.sheet_view.showGridLines = True

    # لوحة الألوان الهندسية
    c_navy = "0B192C"
    c_slate = "1E3E62"
    c_accent = "FF6500"
    c_gold = "FFD166"
    c_bg = "F1F5F9"
    c_white = "FFFFFF"
    c_card_1 = "1E3A8A"
    c_card_2 = "0F766E"
    c_card_3 = "B45309"
    c_card_4 = "4338CA"

    fill_navy = PatternFill(start_color=c_navy, end_color=c_navy, fill_type="solid")
    fill_slate = PatternFill(start_color=c_slate, end_color=c_slate, fill_type="solid")
    fill_bg = PatternFill(start_color=c_bg, end_color=c_bg, fill_type="solid")
    fill_white = PatternFill(start_color=c_white, end_color=c_white, fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_green = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    fill_blue = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    fill_amber = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    thin = Side(style='thin', color='CBD5E1')
    med_navy = Side(style='medium', color=c_navy)
    b_cell = Border(left=thin, right=thin, top=thin, bottom=thin)
    b_card = Border(left=thin, right=thin, top=med_navy, bottom=thin)

    # تجهيز البيانات وتنظيفها
    parsed = []
    for l in raw.split("\n"):
        if "|" in l and not set(l.replace("|", "").strip()).issubset({"-", ":", " "}):
            row_vals = []
            for x in l.split("|"):
                v = x.strip().replace("**", "")
                if v:
                    try: v = float(v) if "." in v else int(v)
                    except ValueError: pass
                    row_vals.append(v)
            if len(row_vals) >= 4:
                parsed.append(row_vals[:5])

    if len(parsed) < 2:
        parsed = [
            ["البند", "القسم", "المحقق", "المستهدف", "ملاحظة"],
            ["مؤشر الكفاءة التشغيلية", "العمليات", 94, 90, "تجاوز المستهدف بنجاح"],
            ["مؤشر جودة المخرجات", "الجودة", 88, 92, "أداء مستقر ومتصاعد"],
            ["مؤشر سرعة الإنجاز", "التطوير", 96, 85, "أعلى معدل أداء"]
        ]

    # تعبئة ورقة البيانات بالمعادلات الحية
    headers = ["البند / الموظف", "الإدارة / التصنيف", "المحقق الفعلي", "المستهدف المخطط", "نسبة الإنجاز %", "الفارق عن المستهدف", "التقييم الآلي", "ملاحظات المتابعة"]
    ws_data.row_dimensions.height = 30
    for col_idx, h_text in enumerate(headers, start=1):
        cell = ws_data.cell(row=1, column=col_idx, value=h_text)
        cell.fill = fill_navy
        cell.font = Font(color=c_gold, bold=True, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = b_cell

    data_rows = parsed[1:]
    last_row = len(data_rows) + 1

    for idx, r in enumerate(data_rows, start=2):
        ws_data.row_dimensions[idx].height = 24
        name_v = r
        dept_v = r[1]
        act_v = r[2] if isinstance(r[2], (int, float)) else 85
        tgt_v = r[3] if isinstance(r[3], (int, float)) else 90
        note_v = r[4] if len(r) > 4 else "متابعة دورية مستمرة"

        row_entries = [
            name_v,
            dept_v,
            act_v,
            tgt_v,
            f"=ROUND((C{idx}/MAX(D{idx},1))*100, 1)",
            f"=C{idx}-D{idx}",
            f'=IF(E{idx}>=100,"متفوق 🌟",IF(E{idx}>=85,"جيد جداً ✅","يحتاج دعم ⚠️"))',
            note_v
        ]

        for c_idx, val in enumerate(row_entries, start=1):
            cell = ws_data.cell(row=idx, column=c_idx, value=val)
            cell.border = b_cell
            cell.font = Font(color="0F172A", size=11, bold=(c_idx in (1, 5)))
            cell.alignment = Alignment(horizontal="center" if c_idx in (3, 4, 5, 6, 7) else "right", vertical="center")
            if idx % 2 == 0: cell.fill = fill_zebra

    # صف الإجماليات والمتوسطات في ورقة البيانات
    tot_row = last_row + 1
    ws_data.row_dimensions[tot_row].height = 28
    tot_entries = [
        "الإجمالي / المتوسط العام",
        f"=COUNTA(A2:A{last_row}) & \" سجل\"",
        f"=SUM(C2:C{last_row})",
        f"=SUM(D2:D{last_row})",
        f"=ROUND(AVERAGE(E2:E{last_row}), 1)",
        f"=SUM(F2:F{last_row})",
        f'=COUNTIF(E2:E{last_row}, ">=85") & " محقق للمعيار"',
        "مؤشر الأداء الكلي"
    ]
    for c_idx, val in enumerate(tot_entries, start=1):
        cell = ws_data.cell(row=tot_row, column=c_idx, value=val)
        cell.fill = fill_slate

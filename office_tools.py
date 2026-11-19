import os, gc, pendulum
from hijridate import Gregorian
from core_ai import sb, ai_ask, send_msg, send_file

def today_dates():
    now = pendulum.now("Asia/Riyadh")
    hijri = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{hijri.day}/{hijri.month}/{hijri.year}هـ - {now.format('YYYY/MM/DD')}م"

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
    outline = ai_ask(msg, "ضع خطة هيكلية احترافية من 5 محاور رئيسية لتغطية هذا الموضوع بعمق أكاديمي وتنفيذي. اكتب كل محور في سطر مستقل بدون مقدمات:")
    sections = [s.strip().lstrip("-*#1234567890. ") for s in outline.split("\n") if len(s.strip()) > 3][:5]
    if not sections:
        sections = ["المقدمة والإطار العام", "التحليل والمنهجية", "التطبيقات العملية", "مؤشرات الأداء والقياس", "النتائج والتوصيات"]

    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = DocPt(14)

    title_p = doc.add_heading(msg[:70], 0); _set_rtl(title_p)
    date_p = doc.add_paragraph(f"تاريخ الإصدار: {today_dates()}"); _set_rtl(date_p)

    for sec in sections:
        h = doc.add_heading(sec, level=1); _set_rtl(h)
        content = ai_ask(f"الموضوع: {msg}\nالمحور المطلوب: {sec}", "اكتب محتوى علمياً وتنفيذياً غزيراً ومفصلاً ومنقحاً باللغة العربية الفصحى مقسماً إلى فقرات وعناوين فرعية:")
        for l in content.split("\n"):
            cl = l.strip().replace("**", "")
            if not cl: continue
            if cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً")):
                sh = doc.add_heading(cl.lstrip("# "), level=2); _set_rtl(sh)
            else:
                p = doc.add_paragraph(cl); _set_rtl(p)

    path = "/tmp/Doc.docx"
    doc.save(path)
    send_file(cid, path, "Executive_Document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 تم إعداد المستند الاحترافي بنجاح\n💡 هل تود تحويل هذا المستند إلى عرض تقديمي أو ملخص تنفيذي؟")
    if os.path.exists(path): os.remove(path)
    del doc; gc.collect()

def make_excel(cid, msg):
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, Reference

    send_msg(cid, "👥 *تفعيل غرفة عمليات لوحة البيانات:*\n1️⃣ وكيل التحليل يبني البيانات الواقعية...\n2️⃣ وكيل المؤشرات يركّب المعادلات والرسوم...")
    prompt_excel = (
        "أنشئ جدول بيانات تنفيذي واقعي وغني بالتفاصيل مكون من 16 صفاً (صف العناوين + 15 صف بيانات حقيقية) و 6 أعمدة بالضبط:\n"
        "العمود 1: اسم البند أو الموظف أو القسم (نص)\n"
        "العمود 2: التصنيف أو الإدارة (نص)\n"
        "العمود 3: القيمة المحققة أو النقاط (رقم صحيح فقط بدون رموز)\n"
        "العمود 4: المستهدف المطلوب (رقم صحيح فقط بدون رموز)\n"
        "العمود 5: نسبة الإنجاز % (رقم صحيح من 60 إلى 100 فقط بدون علامة %)\n"
        "العمود 6: الحالة التنفيذية (ممتاز / جيد جداً / يحتاج تحسين)\n"
        "افصل بين الأعمدة بعلامة | فقط بدون أي مقدمات أو شروحات أو خطوط فصل."
    )
    raw = ai_ask(msg, prompt_excel)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.sheet_view.rightToLeft = True
    ws.sheet_view.showGridLines = True
    ws.title = "لوحة التحكم التنفيذية"

    navy = PatternFill(start_color="0F1C2E", end_color="0F1C2E", fill_type="solid")
    blue_hdr = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    card_bg = PatternFill(start_color="EBF3FA", end_color="EBF3FA", fill_type="solid")
    zebra = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    green_bg = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
    amber_bg = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")

    thin_side = Side(style='thin', color='CBD5E1')
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    ws.merge_cells("A1:F1")
    ws["A1"] = f"📊 لوحة التحكم التحليلية: {msg[:55]}"
    ws["A1"].font = Font(color="FFD166", bold=True, size=15)
    ws["A1"].fill = navy
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("A2:F2")
    ws["A2"] = f"تاريخ التحديث: {today_dates()}  |  نموذج التحليل التنفيذي الآلي"
    ws["A2"].font = Font(color="FFFFFF", size=10)
    ws["A2"].fill = blue_hdr
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    parsed_rows = []
    for l in raw.split("\n"):
        if "|" in l and not set(l.replace("|", "").strip()).issubset({"-", ":", " "}):
            cells = []
            for x in l.split("|"):
                val = x.strip().replace("**", "").replace("%", "")
                if val:
                    try: val = float(val) if "." in val else int(val)
                    except ValueError: pass
                    cells.append(val)
            if len(cells) >= 4:
                parsed_rows.append(cells[:6])

    start_tbl = 7
    end_tbl = start_tbl + max(1, len(parsed_rows) - 1)

    kpi_titles = ["إجمالي السجلات", "مجموع القيم المحققة", "متوسط الإنجاز %", "أعلى أداء مسجل", "متوسط المستهدف", "معدل الكفاءة"]
    kpi_formulas = [
        f"=COUNTA(A{start_tbl+1}:A{end_tbl})",
        f"=SUM(C{start_tbl+1}:C{end_tbl})",
        f"=ROUND(AVERAGE(E{start_tbl+1}:E{end_tbl}),1)",
        f"=MAX(C{start_tbl+1}:C{end_tbl})",
        f"=ROUND(AVERAGE(D{start_tbl+1}:D{end_tbl}),1)",
        f"=ROUND(AVERAGE(C{start_tbl+1}:C{end_tbl})/MAX(AVERAGE(D{start_tbl+1}:D{end_tbl}),1)*100,1)"
    ]
    ws.row_dimensions[4].height = 22
    ws.row_dimensions[5].height = 30
    for idx in range(6):
        c_top = ws.cell(row=4, column=idx+1, value=kpi_titles[idx])
        c_top.font = Font(color="1B365D", bold=True, size=10)
        c_top.fill = card_bg
        c_top.alignment = Alignment(horizontal="center", vertical="center")
        c_top.border = border

        c_val = ws.cell(row=5, column=idx+1, value=kpi_formulas[idx])
        c_val.font = Font(color="0F1C2E", bold=True, size=14)
        c_val.fill = card_bg
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = border

    for r_i, row_data in enumerate(parsed_rows):
        curr_r = start_tbl + r_i
        ws.row_dimensions[curr_r].height = 24
        for c_i, val in enumerate(row_data):
            cell = ws.cell(row=curr_r, column=c_i+1, value=val)
            cell.border = border
            cell.alignment = Alignment(horizontal="center" if c_i >= 2 else "right", vertical="center", wrap_text=True)
            if r_i == 0:
                cell.fill = blue_hdr
                cell.font = Font(color="FFFFFF", bold=True, size=11)
            else:
                cell.font = Font(color="1E293B", size=11)
                if r_i % 2 == 0: cell.fill = zebra
                if c_i == 5:
                    s_val = str(val)
                    if "ممتاز" in s_val: cell.fill = green_bg; cell.font = Font(color="155724", bold=True, size=11)
                    elif "تحسين" in s_val: cell.fill = amber_bg; cell.font = Font(color="856404", bold=True, size=11)

    for idx in range(1, 7):
        col_ltr = get_column_letter(idx)
        max_len = max((len(str(ws.cell(row=r, column=idx).value or "")) for r in range(4, end_tbl+1)), default=12)
        ws.column_dimensions[col_ltr].width = min(max(max_len + 6, 16), 38)

    if len(parsed_rows) > 2:
        try:
            chart = BarChart()
            chart.type = "col"
            chart.style = 10
            chart.title = "مقارنة المحقق مقابل المستهدف"
            chart.y_axis.title = "القيمة"
            chart.x_axis.title = "البند"
            chart.width = 18
            chart.height = 11
            data_ref = Reference(ws, min_col=3, max_col=4, min_row=start_tbl, max_row=end_tbl)
            cats_ref = Reference(ws, min_col=1, min_row=start_tbl+1, max_row=end_tbl)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)
            ws.add_chart(chart, "H4")
        except Exception as e:
            print("Excel Chart Err:", e, flush=True)

    path = "/tmp/Executive_Dashboard.xlsx"
    wb.save(path)
    send_file(cid, path, "Executive_Dashboard.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 تم بناء لوحة التحكم التنفيذية بالمعادلات التلقائية والرسوم البيانية\n💡 هل تود تحويل هذه المؤشرات إلى عرض تقديمي PowerPoint؟")
    if os.path.exists(path): os.remove(path)
    del wb; gc.collect()

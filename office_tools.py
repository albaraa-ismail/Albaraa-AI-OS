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

    send_msg(cid, "👥 *تفعيل غرفة عمليات البيانات:*\n1️⃣ وكيل التحليل يبني الجداول...\n2️⃣ وكيل القياس يولد الرسم البياني...")
    raw = ai_ask(msg, "أنشئ جدول بيانات احترافي من 12 صفاً و 5 أعمدة (اجعل العمود الأول نصي والعمود الثاني رقمي ليصلح للرسم البياني). افصل بين الأعمدة بعلامة | فقط بدون أي نص إضافي أو خطوط فصل:")
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.title = "التحليل والبيانات"
    h_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    z_fill = PatternFill(start_color="F4F7FA", end_color="F4F7FA", fill_type="solid")
    h_font = Font(color="FFFFFF", bold=True, size=12)
    border = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

    row_idx = 0
    for l in raw.split("\n"):
        if "|" in l and not set(l.replace("|", "").strip()).issubset({"-", ":", " "}):
            cells = []
            for x in l.split("|"):
                val = x.strip().replace("**", "")
                if val:
                    try: val = float(val) if "." in val else int(val)
                    except ValueError: pass
                    cells.append(val)
            if cells:
                row_idx += 1; ws.append(cells)
                for col_idx in range(1, len(cells) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
                    cell.border = border
                    if row_idx == 1: cell.fill = h_fill; cell.font = h_font
                    elif row_idx % 2 == 0: cell.fill = z_fill

    for idx, col in enumerate(ws.columns, start=1):
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[get_column_letter(idx)].width = min(max_len + 6, 45)

    if row_idx > 2 and ws.max_column >= 2:
        try:
            chart = BarChart(); chart.title = "التحليل البياني للمؤشرات"; chart.style = 11
            chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=row_idx), titles_from_data=True)
            chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=row_idx))
            ws.add_chart(chart, "G2")
        except Exception: pass

    path = "/tmp/Out.xlsx"
    wb.save(path)
    send_file(cid, path, "Analytics_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 ملف Excel جاهز ومزود برسم بياني\n💡 هل تود عرض هذه النتائج في شرائح PowerPoint؟")
    if os.path.exists(path): os.remove(path)
    del wb; gc.collect()

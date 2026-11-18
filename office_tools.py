import openpyxl
from pptx import Presentation
from docx import Document
from core_ai import sb, ai_ask, send_msg, send_file

def make_kpi(cid):
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(["العملية", "الدور", "الوحدة", "الزمن", "الموفر", "التطور", "المخرج"])
    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50"):
        ws.append([i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")])
    wb.save("/tmp/KPI.xlsx")
    send_file(cid, "/tmp/KPI.xlsx", "KPIs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 جدول القياس")

def make_word(cid, msg):
    send_msg(cid, "⏳ جاري إعداد مستند الوورد...")
    raw = ai_ask(msg, "اكتب تقريراً رسمياً مفصلاً بالعربية بعناوين وفقرات:")
    doc = Document(); doc.add_heading("تقرير رسمي — Albaraa Ai os", 0)
    for l in raw.split("\n"):
        cl = l.strip().replace("**", "")
        if cl: doc.add_heading(cl.lstrip("# "), level=1) if cl.startswith(("#", "أولاً", "ثانياً", "1.", "2.")) else doc.add_paragraph(cl)
    doc.save("/tmp/Doc.docx")
    send_file(cid, "/tmp/Doc.docx", "Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 مستند وورد جاهز")

def make_excel(cid, msg):
    send_msg(cid, "⏳ جاري بناء الإكسل...")
    raw = ai_ask(msg, "اكتب جدولاً، كل سطر صف وتفصل الأعمدة بعلامة | فقط:")
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    for l in raw.split("\n"):
        if "|" in l: ws.append([x.strip() for x in l.split("|") if x.strip()])
    wb.save("/tmp/Out.xlsx")
    send_file(cid, "/tmp/Out.xlsx", "Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 ملف إكسل جاهز")

def make_ppt(cid, msg):
    send_msg(cid, "⏳ جاري تصميم العرض...")
    raw = ai_ask(msg, "صمم 5 شرائح، عنوان كل شريحة بسطر وتحته 3 نقاط، وافصل بسطر فارغ:")
    prs = Presentation(); s0 = prs.slides.add_slide(prs.slide_layouts); s0.shapes.title.text = "Albaraa Ai os"; s0.placeholders.text = msg[:60]
    for blk in [x.strip() for x in raw.split("\n\n") if x.strip()]:
        lns = [l.strip().replace("**", "") for l in blk.split("\n") if l.strip()]
        if lns:
            sl = prs.slides.add_slide(prs.slide_layouts); sl.shapes.title.text = lns[:60]; sl.placeholders.text = "\n".join(lns[1:])
    prs.save("/tmp/Out.pptx")
    send_file(cid, "/tmp/Out.pptx", "Slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ عرض تقديمي جاهز")

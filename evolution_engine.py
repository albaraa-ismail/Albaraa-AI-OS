import openpyxl
from pptx import Presentation
from docx import Document
from core_ai import sb, ai_ask, send_msg, send_file

def make_kpi(cid):
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(["رقم العملية", "المستخدم", "القسم", "زمن التنفيذ(ث)", "الوقت الموفر(د)", "مؤشر التطور%", "المخرج"])
    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50"):
        ws.append([i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")])
    wb.save("/tmp/KPI.xlsx")
    send_file(cid, "/tmp/KPI.xlsx", "Performance_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 تقرير قياس الأداء وتطور الإنجاز")

def make_word(cid, msg):
    send_msg(cid, "⏳ جاري إعداد المستند الاحترافي بدقة عالية...")
    raw = ai_ask(msg, "اكتب مستنداً أكاديمياً وتنفيذياً متكاملاً وعالي الدقة باللغة العربية الفصحى، مقسماً إلى عناوين رئيسية وفقرات تفصيلية عميقة وشاملة:")
    doc = Document(); doc.add_heading(msg[:50], 0)
    for l in raw.split("\n"):
        cl = l.strip().replace("**", "")
        if cl: doc.add_heading(cl.lstrip("# "), level=1) if cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "1.", "2.", "3.", "الفصل")) else doc.add_paragraph(cl)
    doc.save("/tmp/Doc.docx")
    send_file(cid, "/tmp/Doc.docx", "Document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 المستند جاهز")

def make_excel(cid, msg):
    send_msg(cid, "⏳ جاري بناء الجدول...")
    raw = ai_ask(msg, "اكتب بيانات جدول منظم ودقيق، كل سطر صف وتفصل الأعمدة بعلامة | فقط بدون أي نص إضافي:")
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    for l in raw.split("\n"):
        if "|" in l: ws.append([x.strip() for x in l.split("|") if x.strip()])
    wb.save("/tmp/Out.xlsx")
    send_file(cid, "/tmp/Out.xlsx", "Table_Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 ملف البيانات جاهز")

def make_ppt(cid, msg):
    send_msg(cid, "⏳ جاري تصميم العرض التقديمي الاحترافي...")
    raw = ai_ask(msg, "صمم 7 شرائح عرض تقديمي احترافية وعالية الدقة، عنوان كل شريحة بسطر وتحته 4 نقاط مركزة وعميقة، وافصل بين كل شريحة بسطر فارغ:")
    prs = Presentation(); s0 = prs.slides.add_slide(prs.slide_layouts[0]); s0.shapes.title.text = msg[:45]; s0.placeholders[1].text = "عرض تنفيذي وأكاديمي متكامل"
    for blk in [x.strip() for x in raw.split("\n\n") if x.strip()]:
        lns = [l.strip().replace("**", "") for l in blk.split("\n") if l.strip()]
        if lns:
            sl = prs.slides.add_slide(prs.slide_layouts[1]); sl.shapes.title.text = lns[0][:60]; sl.placeholders[1].text = "\n".join(lns[1:])
    prs.save("/tmp/Out.pptx")
    send_file(cid, "/tmp/Out.pptx", "Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ العرض التقديمي جاهز")

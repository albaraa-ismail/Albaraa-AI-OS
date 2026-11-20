import os
import re
import gc
import json
import pendulum
from hijridate import Gregorian
from core.core_ai import sb, ai_ask, ai_ask_json, send_msg, send_file
from core.event_bus import BUS
from security.safe_guard import apply_saudi_governance


def _dates():
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ - {now.format('YYYY/MM/DD')}م"


def _export_styled_doc(cid: str, title: str, body: str, domain_tag: str, file_prefix: str):
    from docx import Document
    from docx.shared import Pt as DocPt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import nsdecls

    governed_body = apply_saudi_governance(domain_tag, body)

    def _rtl(p):
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p._p.get_or_add_pPr().append(OxmlElement('w:bidi'))

    doc = Document()
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = DocPt(12.5)

    tbl = doc.add_table(rows=1, cols=1)
    cell = tbl.cell(0, 0)
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="0B192C"/>'))
    p0 = cell.paragraphs
    _rtl(p0)
    r0 = p0.add_run(f"{title}\n")
    r0.font.name = 'Arial'; r0.font.size = DocPt(18); r0.font.bold = True; r0.font.color.rgb = RGBColor(255, 209, 102)
    r1 = p0.add_run(f"تاريخ الإصدار: {_dates()}  |  {domain_tag}")
    r1.font.name = 'Arial'; r1.font.size = DocPt(10.5); r1.font.color.rgb = RGBColor(255, 255, 255)

    for line in governed_body.split("\n"):
        cl = line.strip().replace("**", "")
        if not cl or cl.startswith("<!--"):
            continue
        p = doc.add_paragraph()
        _rtl(p)
        run = p.add_run(cl.lstrip("# "))
        run.font.name = 'Arial'
        if cl.startswith(("#", "1.", "2.", "3.", "4.", "5.", "أولاً", "ثانياً", "ثالثاً")):
            run.font.size = DocPt(14.5); run.font.bold = True; run.font.color.rgb = RGBColor(11, 25, 44)
        else:
            run.font.size = DocPt(12.5); run.font.color.rgb = RGBColor(30, 41, 59)

    safe_name = re.sub(r'[^\w\s-]', '', file_prefix).strip().replace(" ", "_") or "Document"
    out_path = f"/tmp/{safe_name}.docx"
    doc.save(out_path)
    send_file(cid, out_path, f"{safe_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📄 *{title}* ({_dates()})")
    if os.path.exists(out_path):
        os.remove(out_path)
    del doc
    gc.collect()
def run_pro_capability(cid: str, task: str, category: str = "general"):
    low = task.lower()

    # 1. التجارة الإلكترونية وإدارة المتاجر (22 - 26)
    if category == "ecommerce" or any(k in low for k in ("سلة", "زد", "متجر", "منتج", "سلة متروكة", "تسعير")):
        send_msg(cid, "🛍️ جاري إعداد ملف التجارة الإلكترونية وتحسين محركات البحث (SEO) وفق الأنظمة السعودية...")
        prompt = (
            f"أنت خبير تجارة إلكترونية ونمو متاجر في السوق السعودي (سلة وزد). للمهمة التالية: {task}\n"
            "أعدّ دراسة تنفيذية شاملة تتضمن:\n"
            "1. صياغة تسويقية احترافية وجذابة متوافقة مع محركات البحث (SEO) والكلمات المفتاحية الأعلى بحثاً في السعودية.\n"
            "2. استراتيجية التسعير التنافسي ورسائل استرجاع السلات المتروكة لزيادة معدل التحويل.\n"
            "3. ضوابط الامتثال لنظام التجارة الإلكترونية السعودي وحماية المستهلك."
        )
        res = ai_ask(task, prompt, mode="arabic")
        _export_styled_doc(cid, "حزمة تطوير المتاجر والتجارة الإلكترونية", res, "التجارة الإلكترونية والامتثال", "Ecommerce_Kit")
        BUS.publish("pro.ecommerce", {"cid": cid})
        return

    # 2. الموارد البشرية والتوظيف والتدريب (27 - 31)
    if category == "hr" or any(k in low for k in ("سيرة ذاتية", "توظيف", "مقابلة", "وصف وظيفي", "حقيبة تدريبية", "فجوات المهارات")):
        send_msg(cid, "👥 جاري إعداد ملف الموارد البشرية والتقييم الوظيفي وفق نظام العمل السعودي...")
        prompt = (
            f"أنت مدير موارد بشرية وتطوير تنظيمي خبير بنظام العمل السعودي. للمهمة التالية: {task}\n"
            "أعدّ وثيقة احترافية تشمل حسب الطلب: (بطاقة الوصف الوظيفي، مؤشرات الأداء KPIs، أسئلة المقابلات التخصصية، معايير فرز المرشحين، وخطة سد فجوات المهارات)."
        )
        res = ai_ask(task, prompt, mode="arabic")
        _export_styled_doc(cid, "ملف الموارد البشرية والتطوير الوظيفي", res, "الموارد البشرية ونظام العمل", "HR_Package")
        BUS.publish("pro.hr", {"cid": cid})
        return

    # 3. العقارات والمقاولات وإدارة المشاريع الهندسية (32 - 36)
    if category == "engineering" or any(k in low for k in ("كميات", "مقاولات", "عقار", "جدوى عقارية", "مناقصة", "ترسية", "مخطط زمني")):
        send_msg(cid, "🏗️ جاري إعداد الدراسة الهندسية وحساب الكميات والجدوى الاستثمارية...")
        prompt = (
            f"أنت مهندس مشاريع وخبير دراسات جدوى عقارية ومناقصات في المملكة. للمشروع التالي: {task}\n"
            "أعدّ ملفاً فنياً ومالياً دقيقاً يشمل: جدول الكميات والتكاليف التقديرية، تحليل العائد الاستثماري والمخاطر التشغيلية، والجدول الزمني للتنفيذ."
        )
        res = ai_ask(task, prompt, mode="arabic")
        _export_styled_doc(cid, "الدراسة الهندسية والجدوى الاستثمارية", res, "الهندسة والعقارات والمناقصات", "Engineering_Study")
        BUS.publish("pro.engineering", {"cid": cid})
        return

    # 4. القانون والحوكمة والعقود والخطابات الرسمية (37 - 41)
    if category == "legal" or any(k in low for k in ("عقد", "اتفاقية", "لائحة", "نظام", "محضر اجتماع", "خطاب رسمي", "معروض", "حوكمة")):
        send_msg(cid, "⚖️ جاري صياغة الوثيقة القانونية / الرسمية ومطابقتها للأنظمة السعودية...")
        prompt = (
            f"أنت مستشار قانوني وصائغ عقود وخطابات رسمية خبير بالأنظمة السعودية (نظام العمل، نظام المعاملات المدنية، نظام حماية البيانات PDPL). للمهمة التالية: {task}\n"
            "اصغ الوثيقة بأعلى درجات الدقة القانونية واللغوية الرسمية مع توضيح الالتزامات والحقوق بوضوح تام."
        )
        res = ai_ask(task, prompt, mode="arabic")
        _export_styled_doc(cid, "الوثيقة القانونية والحوكمة النظامية", res, "عقد واتفاقية نظامية", "Legal_Governance_Doc")
        BUS.publish("pro.legal", {"cid": cid})
        return

    # 5. الفوترة الضريبية وعروض الأسعار ZATCA
    if category == "finance" or any(k in low for k in ("فاتورة", "عرض سعر", "ضريبة", "زكاة", "قائمة مالية")):
        send_msg(cid, "🧾 جاري إصدار العرض المالي / الفاتورة الضريبية المتوافقة مع متطلبات ZATCA...")
        prompt = (
            f"أنت محاسب قانوني معتمد في السعودية. للمهمة التالية: {task}\n"
            "أعدّ جدولاً مالياً دقيقاً يوضح البنود، الأسعار الإفرادية، الإجمالي قبل الضريبة، ضريبة القيمة المضافة 15%، والإجمالي النهائي شامل الضريبة."
        )
        res = ai_ask(task, prompt, mode="fast")
        _export_styled_doc(cid, "بيان مالي وضريبي معتمد", res, "فاتورة وضريبة ZATCA", "Financial_Statement")
        BUS.publish("pro.finance", {"cid": cid})
        return

    # 6. التسويق الرقمي والحملات والسيناريوهات (42 - 50)
    send_msg(cid, "🚀 جاري إعداد الخطة التسويقية وصناعة المحتوى الاحترافي...")
    prompt = (
        f"أنت مدير تسويق رقمي وصانع محتوى إبداعي للسوق السعودي والخليجي. للمهمة التالية: {task}\n"
        "أعدّ ملفاً تنفيذياً متكاملاً يشمل: النصوص الإعلانية عالية التحويل (لمنصات X وسناب شات وتيك توك)، سيناريو الفيديو الترويجي، وخطة الاستهداف."
    )
    res = ai_ask(task, prompt, mode="arabic")
    _export_styled_doc(cid, "الخطة التسويقية وصناعة المحتوى", res, "التسويق الرقمي والإعلام", "Marketing_Campaign")
    BUS.publish("pro.marketing", {"cid": cid})


def make_pdf_report(cid: str, task: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    import arabic_reshaper
    from bidi.algorithm import get_display

    send_msg(cid, "📑 جاري إعداد وتصدير ملف PDF الرسمي المنسّق...")
    content = ai_ask(task, "اكتب تقريراً رسمياً موجزاً ومنظماً باللغة العربية الفصحى في نقاط واضحة:", mode="arabic")
    governed = apply_saudi_governance(task, content)

    path = "/tmp/Official_Report.pdf"
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 60

    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 40, y, get_display(arabic_reshaper.reshape(f"تقرير رسمي - {_dates()}")))
    y -= 30
    c.setFont("Helvetica", 11)

    for raw_line in governed.split("\n"):
        clean = raw_line.strip().replace("**", "").replace("#", "")
        if not clean or clean.startswith("<!--"):
            continue
        for i in range(0, len(clean), 75):
            chunk = clean[i:i+75]
            reshaped = get_display(arabic_reshaper.reshape(chunk))
            c.drawRightString(width - 40, y, reshaped)
            y -= 18
            if y < 60:
                c.showPage()
                y = height - 60

    c.save()
    send_file(cid, path, "Official_Report.pdf", "application/pdf", f"📑 تم إصدار التقرير الرسمي بصيغة PDF ({_dates()})")
    if os.path.exists(path):
        os.remove(path)

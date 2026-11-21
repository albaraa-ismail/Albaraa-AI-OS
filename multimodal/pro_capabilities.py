import gc
import json
import os
import re
from typing import Any
import pendulum
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt as DocPt, RGBColor
from hijridate import Gregorian

from core.core_ai import ai_ask, ai_ask_json, sb, send_file, send_msg
from core.event_bus import BUS
from security.safe_guard import apply_saudi_governance

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _dates() -> str:
    """إرجاع التاريخ الهجري والميلادي الحالي بتوقيت الرياض."""
    now = pendulum.now("Asia/Riyadh")
    hijri = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{hijri.day}/{hijri.month}/{hijri.year}هـ - {now.format('YYYY/MM/DD')}م"


def _style_run(run: Any, size: float, color: RGBColor, bold: bool = False) -> None:
    """تطبيق تنسيق الخط الموحد على فقرات Word."""
    run.font.name = "Arial"
    run.font.size = DocPt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _set_rtl(paragraph: Any) -> None:
    """ضبط اتجاه الفقرة من اليمين إلى اليسار (RTL)."""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph._p.get_or_add_pPr().append(OxmlElement("w:bidi"))


def _export_styled_doc(cid: str, title: str, body: str, domain_tag: str, file_prefix: str) -> None:
    """توليد وإرسال مستند Word منسق بالكامل بالهوية البصرية الرسمية."""
    governed_body = apply_saudi_governance(domain_tag, body)
    date_str = _dates()

    doc = Document()
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = DocPt(12.5)

    # ترويسة المستند
    tbl = doc.add_table(rows=1, cols=1)
    cell = tbl.cell(0, 0)
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="0B192C"/>'))
    p0 = cell.paragraphs
    _set_rtl(p0)
    _style_run(p0.add_run(f"{title}\n"), 18, RGBColor(255, 209, 102), bold=True)
    _style_run(p0.add_run(f"تاريخ الإصدار: {date_str}  |  {domain_tag}"), 10.5, RGBColor(255, 255, 255))

    # محتوى المستند
    heading_prefixes = ("#", "1.", "2.", "3.", "4.", "5.", "أولاً", "ثانياً", "ثالثاً")
    for line in governed_body.split("\n"):
        cl = line.strip().replace("**", "")
        if not cl or cl.startswith("<!--"):
            continue
        p = doc.add_paragraph()
        _set_rtl(p)
        is_heading = cl.startswith(heading_prefixes)
        _style_run(
            p.add_run(cl.lstrip("# ")),
            size=14.5 if is_heading else 12.5,
            color=RGBColor(11, 25, 44) if is_heading else RGBColor(30, 41, 59),
            bold=is_heading,
        )

    safe_name = re.sub(r"[^\w\s-]", "", file_prefix).strip().replace(" ", "_") or "Document"
    out_path = f"/tmp/{safe_name}.docx"
    doc.save(out_path)
    send_file(cid, out_path, f"{safe_name}.docx", DOCX_MIME, f"📄 *{title}* ({date_str})")

    if os.path.exists(out_path):
        os.remove(out_path)
    del doc
    gc.collect()
CAPABILITY_SPECS: list[dict[str, Any]] = [
    {
        "category": "ecommerce",
        "keywords": ("سلة", "زد", "متجر", "منتج", "سلة متروكة", "تسعير"),
        "status": "🛍️ جاري إعداد ملف التجارة الإلكترونية وتحسين محركات البحث (SEO) وفق الأنظمة السعودية...",
        "title": "حزمة تطوير المتاجر والتجارة الإلكترونية",
        "domain": "التجارة الإلكترونية والامتثال",
        "prefix": "Ecommerce_Kit",
        "event": "pro.ecommerce",
        "mode": "arabic",
        "prompt": (
            "أنت خبير تجارة إلكترونية ونمو متاجر في السوق السعودي (سلة وزد). للمهمة التالية: {task}\n"
            "أعدّ دراسة تنفيذية شاملة تتضمن:\n"
            "1. صياغة تسويقية احترافية وجذابة متوافقة مع محركات البحث (SEO) والكلمات المفتاحية الأعلى بحثاً في السعودية.\n"
            "2. استراتيجية التسعير التنافسي ورسائل استرجاع السلات المتروكة لزيادة معدل التحويل.\n"
            "3. ضوابط الامتثال لنظام التجارة الإلكترونية السعودي وحماية المستهلك."
        ),
    },
    {
        "category": "hr",
        "keywords": ("سيرة ذاتية", "توظيف", "مقابلة", "وصف وظيفي", "حقيبة تدريبية", "فجوات المهارات"),
        "status": "👥 جاري إعداد ملف الموارد البشرية والتقييم الوظيفي وفق نظام العمل السعودي...",
        "title": "ملف الموارد البشرية والتطوير الوظيفي",
        "domain": "الموارد البشرية ونظام العمل",
        "prefix": "HR_Package",
        "event": "pro.hr",
        "mode": "arabic",
        "prompt": (
            "أنت مدير موارد بشرية وتطوير تنظيمي خبير بنظام العمل السعودي. للمهمة التالية: {task}\n"
            "أعدّ وثيقة احترافية تشمل حسب الطلب: (بطاقة الوصف الوظيفي، مؤشرات الأداء KPIs، أسئلة المقابلات التخصصية، معايير فرز المرشحين، وخطة سد فجوات المهارات)."
        ),
    },
    {
        "category": "engineering",
        "keywords": ("كميات", "مقاولات", "عقار", "جدوى عقارية", "مناقصة", "ترسية", "مخطط زمني"),
        "status": "🏗️ جاري إعداد الدراسة الهندسية وحساب الكميات والجدوى الاستثمارية...",
        "title": "الدراسة الهندسية والجدوى الاستثمارية",
        "domain": "الهندسة والعقارات والمناقصات",
        "prefix": "Engineering_Study",
        "event": "pro.engineering",
        "mode": "arabic",
        "prompt": (
            "أنت مهندس مشاريع وخبير دراسات جدوى عقارية ومناقصات في المملكة. للمشروع التالي: {task}\n"
            "أعدّ ملفاً فنياً ومالياً دقيقاً يشمل: جدول الكميات والتكاليف التقديرية، تحليل العائد الاستثماري والمخاطر التشغيلية، والجدول الزمني للتنفيذ."
        ),
    },
    {
        "category": "legal",
        "keywords": ("عقد", "اتفاقية", "لائحة", "نظام", "محضر اجتماع", "خطاب رسمي", "معروض", "حوكمة"),
        "status": "⚖️ جاري صياغة الوثيقة القانونية / الرسمية ومطابقتها للأنظمة السعودية...",
        "title": "الوثيقة القانونية والحوكمة النظامية",
        "domain": "عقد واتفاقية نظامية",
        "prefix": "Legal_Governance_Doc",
        "event": "pro.legal",
        "mode": "arabic",
        "prompt": (
            "أنت مستشار قانوني وصائغ عقود وخطابات رسمية خبير بالأنظمة السعودية (نظام العمل، نظام المعاملات المدنية، نظام حماية البيانات PDPL). للمهمة التالية: {task}\n"
            "اصغ الوثيقة بأعلى درجات الدقة القانونية واللغوية الرسمية مع توضيح الالتزامات والحقوق بوضوح تام."
        ),
    },
    {
        "category": "finance",
        "keywords": ("فاتورة", "عرض سعر", "ضريبة", "زكاة", "قائمة مالية"),
        "status": "🧾 جاري إصدار العرض المالي / الفاتورة الضريبية المتوافقة مع متطلبات ZATCA...",
        "title": "بيان مالي وضريبي معتمد",
        "domain": "فاتورة وضريبة ZATCA",
        "prefix": "Financial_Statement",
        "event": "pro.finance",
        "mode": "fast",
        "prompt": (
            "أنت محاسب قانوني معتمد في السعودية. للمهمة التالية: {task}\n"
            "أعدّ جدولاً مالياً دقيقاً يوضح البنود، الأسعار الإفرادية، الإجمالي قبل الضريبة، ضريبة القيمة المضافة 15%، والإجمالي النهائي شامل الضريبة."
        ),
    },
]

DEFAULT_MARKETING_SPEC: dict[str, Any] = {
    "status": "🚀 جاري إعداد الخطة التسويقية وصناعة المحتوى الاحترافي...",
    "title": "الخطة التسويقية وصناعة المحتوى",
    "domain": "التسويق الرقمي والإعلام",
    "prefix": "Marketing_Campaign",
    "event": "pro.marketing",
    "mode": "arabic",
    "prompt": (
        "أنت مدير تسويق رقمي وصانع محتوى إبداعي للسوق السعودي والخليجي. للمهمة التالية: {task}\n"
        "أعدّ ملفاً تنفيذياً متكاملاً يشمل: النصوص الإعلانية عالية التحويل (لمنصات X وسناب شات وتيك توك)، سيناريو الفيديو الترويجي، وخطة الاستهداف."
    ),
}


def run_pro_capability(cid: str, task: str, category: str = "general") -> None:
    """تنفيذ القدرات التخصصية وتصديرها كمستندات احترافية معتمدة."""
    low = task.lower()
    spec = next(
        (s for s in CAPABILITY_SPECS if category == s["category"] or any(k in low for k in s["keywords"])),
        DEFAULT_MARKETING_SPEC,
    )
    send_msg(cid, spec["status"])
    res = ai_ask(task, spec["prompt"].format(task=task), mode=spec["mode"])
    _export_styled_doc(cid, spec["title"], res, spec["domain"], spec["prefix"])
    BUS.publish(spec["event"], {"cid": cid})


def _ar_pdf_text(text: str) -> str:
    """تشكيل وضبط اتجاه النص العربي للرسم في ملفات PDF."""
    import arabic_reshaper
    from bidi.algorithm import get_display

    return get_display(arabic_reshaper.reshape(text))


def make_pdf_report(cid: str, task: str) -> None:
    """توليد وتصدير تقرير رسمي بصيغة PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    send_msg(cid, "📑 جاري إعداد وتصدير ملف PDF الرسمي المنسّق...")
    content = ai_ask(task, "اكتب تقريراً رسمياً موجزاً ومنظماً باللغة العربية الفصحى في نقاط واضحة:", mode="arabic")
    governed = apply_saudi_governance(task, content)

    path = "/tmp/Official_Report.pdf"
    pdf = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 60

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawRightString(width - 40, y, _ar_pdf_text(f"تقرير رسمي - {_dates()}"))
    y -= 30
    pdf.setFont("Helvetica", 11)

    for raw_line in governed.split("\n"):
        clean = raw_line.strip().replace("**", "").replace("#", "")
        if not clean or clean.startswith("<!--"):
            continue
        for i in range(0, len(clean), 75):
            pdf.drawRightString(width - 40, y, _ar_pdf_text(clean[i : i + 75]))
            y -= 18
            if y < 60:
                pdf.showPage()
                y = height - 60

    pdf.save()
    send_file(cid, path, "Official_Report.pdf", "application/pdf", f"📑 تم إصدار التقرير الرسمي بصيغة PDF ({_dates()})")
    if os.path.exists(path):
        os.remove(path)

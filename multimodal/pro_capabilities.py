import gc
import os
import re
import uuid
import base64
import struct
from typing import Any
import requests
import pendulum
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt as DocPt, RGBColor
from hijridate import Gregorian

from core.config import GREEN_BASE, GREEN_ID, GREEN_TOKEN
from core.core_ai import ai_ask, ai_ask_json, sb
from core.event_bus import BUS
from core.orchestrator import send_msg
from security.safe_guard import apply_saudi_governance

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def send_file(cid: str, file_path: str, filename: str, mime: str = DOCX_MIME, caption: str = "") -> bool:
    if not (GREEN_ID and GREEN_TOKEN and cid and os.path.exists(file_path)):
        return False
    chat_id = cid if "@" in cid else f"{cid}@c.us"
    base = GREEN_BASE.rstrip("/")
    if "waInstance" in base:
        url = f"{base}/sendFileByUpload/{GREEN_TOKEN}"
    else:
        url = f"{base}/waInstance{GREEN_ID}/sendFileByUpload/{GREEN_TOKEN}"
    try:
        with open(file_path, "rb") as f:
            res = requests.post(
                url,
                data={"chatId": chat_id, "fileName": filename, "caption": caption},
                files={"file": (filename, f, mime)},
                timeout=35,
            )
        if res.status_code == 200:
            return True
        print(f"WA File Err [{res.status_code}]: {res.text[:120]}", flush=True)
        return False
    except Exception as exc:
        print(f"WA File Err: {exc}", flush=True)
        return False


def _dates() -> str:
    now = pendulum.now("Asia/Riyadh")
    hijri = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{hijri.day}/{hijri.month}/{hijri.year}هـ - {now.format('YYYY/MM/DD')}م"


def _style_run(run: Any, size: float, color: RGBColor, bold: bool = False) -> None:
    run.font.name = "Arial"
    run.font.size = DocPt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _set_rtl(paragraph: Any) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph._p.get_or_add_pPr().append(OxmlElement("w:bidi"))


def _export_styled_doc(cid: str, title: str, body: str, domain_tag: str, file_prefix: str) -> None:
    governed_body = apply_saudi_governance(domain_tag, body)
    date_str = _dates()

    doc = Document()
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = DocPt(12.5)

    tbl = doc.add_table(rows=1, cols=1)
    cell = tbl.cell(0, 0)
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="0B192C"/>'))
    p0 = cell.paragraphs[0]
    _set_rtl(p0)
    _style_run(p0.add_run(f"{title}\n"), 18, RGBColor(255, 209, 102), bold=True)
    _style_run(p0.add_run(f"تاريخ الإصدار: {date_str}  |  {domain_tag}"), 10.5, RGBColor(255, 255, 255))

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
    out_path = f"/tmp/{safe_name}_{uuid.uuid4().hex[:6]}.docx"
    doc.save(out_path)
    send_file(cid, out_path, f"{safe_name}.docx", DOCX_MIME, f"📄 *{title}* ({date_str})")

    if os.path.exists(out_path):
        os.remove(out_path)
    del doc
    gc.collect()


def build_zatca_qr_base64(seller: str, vat_num: str, total: float, vat_amount: float) -> str:
    ts = pendulum.now("Asia/Riyadh").to_iso8601_string()
    tags = (
        (1, seller.encode("utf-8")),
        (2, vat_num.encode("utf-8")),
        (3, ts.encode("utf-8")),
        (4, f"{total:.2f}".encode("utf-8")),
        (5, f"{vat_amount:.2f}".encode("utf-8")),
    )
    tlv = b"".join(struct.pack("BB", tag, len(val)) + val for tag, val in tags)
    return base64.b64encode(tlv).decode("utf-8")


SAUDI_REGULATORY_MATRIX: dict[str, dict[str, Any]] = {
    "ecommerce": {
        "keywords": ("سلة", "زد", "متجر", "منتج", "سلة متروكة", "تسعير"),
        "status": "🛍️ جاري إعداد ملف التجارة الإلكترونية وتحسين SEO وفق نظام التجارة الإلكترونية السعودي...",
        "title": "حزمة تطوير المتاجر والتجارة الإلكترونية",
        "domain": "التجارة الإلكترونية والامتثال",
        "prefix": "Ecommerce_Kit",
        "event": "pro.ecommerce",
        "mode": "arabic",
        "standards": "نظام التجارة الإلكترونية السعودي، لوائح حماية المستهلك، الإفصاح الضريبي 15%.",
    },
    "hr": {
        "keywords": ("سيرة ذاتية", "توظيف", "مقابلة", "وصف وظيفي", "حقيبة تدريبية", "فجوات المهارات"),
        "status": "👥 جاري إعداد ملف الموارد البشرية وفق نظام العمل السعودي ونطاقات...",
        "title": "ملف الموارد البشرية والتطوير الوظيفي",
        "domain": "الموارد البشرية ونظام العمل",
        "prefix": "HR_Package",
        "event": "pro.hr",
        "mode": "arabic",
        "standards": "نظام العمل السعودي (المواد 50-88)، لائحة تنظيم العمل، مؤشرات الأداء KPIs.",
    },
    "engineering": {
        "keywords": ("كميات", "مقاولات", "عقار", "جدوى عقارية", "مناقصة", "ترسية", "مخطط زمني"),
        "status": "🏗️ جاري إعداد الدراسة الهندسية وحساب الكميات والجدوى الاستثمارية...",
        "title": "الدراسة الهندسية والجدوى الاستثمارية",
        "domain": "الهندسة والعقارات والمناقصات",
        "prefix": "Engineering_Study",
        "event": "pro.engineering",
        "mode": "arabic",
        "standards": "كود البناء السعودي (SBC)، نظام المنافسات والمشتريات الحكومية، تحليل ROI وNPV.",
    },
    "legal": {
        "keywords": ("عقد", "اتفاقية", "لائحة", "نظام", "محضر اجتماع", "خطاب رسمي", "معروض", "حوكمة"),
        "status": "⚖️ جاري صياغة الوثيقة القانونية ومطابقتها للأنظمة السعودية...",
        "title": "الوثيقة القانونية والحوكمة النظامية",
        "domain": "عقد واتفاقية نظامية",
        "prefix": "Legal_Governance_Doc",
        "event": "pro.legal",
        "mode": "arabic",
        "standards": "نظام المعاملات المدنية، نظام العمل، نظام حماية البيانات الشخصية (PDPL).",
    },
    "finance": {
        "keywords": ("فاتورة", "عرض سعر", "ضريبة", "زكاة", "قائمة مالية"),
        "status": "🧾 جاري إصدار العرض المالي / الفاتورة الضريبية المتوافقة مع ZATCA...",
        "title": "بيان مالي وضريبي معتمد (ZATCA)",
        "domain": "فاتورة وضريبة ZATCA",
        "prefix": "Financial_Statement",
        "event": "pro.finance",
        "mode": "fast",
        "standards": "لائحة الفوترة الإلكترونية (ZATCA المرحلة الثانية)، ضريبة القيمة المضافة 15%.",
    },
}

DEFAULT_SPEC: dict[str, Any] = {
    "status": "🚀 جاري إعداد الخطة التسويقية وصناعة المحتوى الاحترافي...",
    "title": "الخطة التسويقية وصناعة المحتوى",
    "domain": "التسويق الرقمي والإعلام",
    "prefix": "Marketing_Campaign",
    "event": "pro.marketing",
    "mode": "arabic",
    "standards": "ضوابط الهيئة العامة لتنظيم الإعلام، استراتيجيات التحويل الرقمي في السوق السعودي.",
}


def run_pro_capability(cid: str, task: str, category: str = "general") -> None:
    low = task.lower()
    spec = SAUDI_REGULATORY_MATRIX.get(category) or next(
        (s for s in SAUDI_REGULATORY_MATRIX.values() if any(k in low for k in s["keywords"])),
        DEFAULT_SPEC,
    )
    send_msg(cid, spec["status"])
    sys_prompt = (
        f"أنت خبير استشاري تنفيذي في {spec['domain']}. المعايير الملزمة: {spec['standards']}\n"
        "أعد وثيقة احترافية دقيقة، منظمة في جداول ونقاط تنفيذية وأرقام واقعية دون مقدمات آلية."
    )
    res = ai_ask(task, sys_prompt, mode=spec["mode"])
    if spec["event"] == "pro.finance":
        nums = [float(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", task) if float(x) > 10]
        subtotal = sum(nums) if nums else 1000.0
        vat = round(subtotal * 0.15, 2)
        total = round(subtotal + vat, 2)
        qr_b64 = build_zatca_qr_base64("Albaraa-AI-OS", "300000000000003", total, vat)
        res += f"\n\n---\n### ملخص الربط الضريبي (ZATCA TLV)\n• الإجمالي قبل الضريبة: {subtotal:.2f} ريال\n• ضريبة القيمة المضافة (15%): {vat:.2f} ريال\n• الإجمالي شامل الضريبة: {total:.2f} ريال\n• رمز التشفير الضريبي (Base64 TLV): {qr_b64}"

    _export_styled_doc(cid, spec["title"], res, spec["domain"], spec["prefix"])
    BUS.publish(spec["event"], {"cid": cid})


def _ar_pdf_text(text: str) -> str:
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def _register_arabic_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("ArabicFont", fp))
                return "ArabicFont"
            except Exception:
                continue
    return "Helvetica"


def make_pdf_report(cid: str, task: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    send_msg(cid, "📑 جاري إعداد وتصدير ملف PDF الرسمي المنسّق...")
    content = ai_ask(task, "اكتب تقريرا رسميا موجزا ومنظما باللغة العربية الفصحى في نقاط واضحة:", mode="arabic")
    governed = apply_saudi_governance(task, content)

    font_name = _register_arabic_font()
    path = f"/tmp/Official_Report_{uuid.uuid4().hex[:6]}.pdf"
    pdf = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 60

    pdf.setFont(font_name, 14)
    pdf.drawRightString(width - 40, y, _ar_pdf_text(f"تقرير رسمي - {_dates()}"))
    y -= 30
    pdf.setFont(font_name, 11)

    for raw_line in governed.split("\n"):
        clean = raw_line.strip().replace("**", "").replace("#", "")
        if not clean or clean.startswith("<!--"):
            continue
        for i in range(0, len(clean), 75):
            pdf.drawRightString(width - 40, y, _ar_pdf_text(clean[i : i + 75]))
            y -= 18
            if y < 60:
                pdf.showPage()
                pdf.setFont(font_name, 11)
                y = height - 60

    pdf.save()
    send_file(cid, path, "Official_Report.pdf", "application/pdf", f"📑 تم إصدار التقرير الرسمي بصيغة PDF ({_dates()})")
    if os.path.exists(path):
        os.remove(path)
    del pdf
    gc.collect()

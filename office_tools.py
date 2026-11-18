import os
import re
import json
import zipfile
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from docx import Document
from docx.shared import Pt as DocPt, RGBColor as DocRGB
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from core_ai import sb, ai_ask, send_msg, send_file

# ألوان الهوية البصرية لمنظومة Albaraa AI OS
NAVY_HEX = "0F172A"
ROYAL_HEX = "1E3A8A"
GOLD_HEX = "D97706"
LIGHT_BG_HEX = "F8FAFC"

def _extract_json(raw: str):
    """استخراج كائن JSON من رد الذكاء الاصطناعي بدقة حتى لو أضاف نصًا حوله"""
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None

def _set_rtl_paragraph(p):
    """تفعيل اتجاه الكتابة من اليمين لليسار (RTL) في مستندات الوورد"""
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)

def _style_excel_sheet(ws, headers, rows):
    """تنسيق جداول الإكسل بهوية بصرية احترافية وحدود وضبط تلقائي للأعمدة"""
    ws.sheet_view.rightToLeft = True
    header_fill = PatternFill(start_color=NAVY_HEX, end_color=NAVY_HEX, fill_type="solid")
    zebra_fill = PatternFill(start_color=LIGHT_BG_HEX, end_color=LIGHT_BG_HEX, fill_type="solid")
    header_font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    body_font = Font(name="Arial", size=11, color="1E293B")
    thin_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    ws.append(headers)
    ws.row_dimensions[1].height = 28
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border

    for r_idx, row_data in enumerate(rows, start=2):
        ws.append(row_data)
        ws.row_dimensions[r_idx].height = 22
        for c_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.font = body_font
            cell.border = cell_border
            cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            if r_idx % 2 == 0:
                cell.fill = zebra_fill

    for col in ws.columns:
        max_len = 12
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_len = len(str(cell.value or ""))
            if val_len > max_len:
                max_len = min(val_len + 5, 45)
        ws.column_dimensions[col_letter].width = max_len

def make_kpi(cid):
    send_msg(cid, "⏳ جاري استخراج وتنسيق تقرير مؤشرات الأداء (KPIs)...")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "مؤشرات الأداء"
    headers = ["رقم العملية", "الصلاحية", "الوحدة", "زمن الاستجابة (ث)", "الوقت الموفر (د)", "مؤشر التطور", "نوع المخرج"]
    rows = []
    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50"):
        rows.append([
            i.get("id"), i.get("user_role"), i.get("unit_used"),
            i.get("response_time_sec"), i.get("time_saved_min"),
            i.get("user_growth_score"), i.get("deliverable_type")
        ])
    _style_excel_sheet(ws, headers, rows or [["-", "لا توجد بيانات مسجلة بعد", "-", "-", "-", "-", "-"]])
    path = "/tmp/Albaraa_KPIs.xlsx"
    wb.save(path)
    send_file(cid, path, "Albaraa_KPIs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 تقرير مؤشرات الأداء التنفيذي جاهز")

def make_word(cid, msg):
    send_msg(cid, "⏳ جاري صياغة وتنسيق المستند الرسمي (Word)...")
    sys_prompt = (
        "أنت مستشار تنفيذي خبير. اكتب مستنداً رسمياً متكاملاً واحترافياً باللغة العربية الفصحى حول طلب المستخدم. "
        "أرجع النتيجة بصيغة JSON فقط بدون أي كلام خارجها بهذا الهيكل الدقيق:\n"
        '{"title": "عنوان المستند الرئيسي", "subtitle": "ملخص تنفيذي سطر واحد", '
        '"sections": [{"heading": "عنوان القسم", "paragraphs": ["فقرة تفصيلية أولى", "فقرة ثانية"], "bullets": ["نقطة رئيسية 1", "نقطة رئيسية 2"]}]}'
    )
    raw = ai_ask(msg, sys_prompt)
    data = _extract_json(raw)

    doc = Document()
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # ترويسة الصفحة (Header)
    header = doc.sections[0].header
    hp = header.paragraphs[0]
    hp.text = f"منظومة Albaraa AI OS التنفيذية  |  التاريخ: {today_str}"
    _set_rtl_paragraph(hp)
    hp.runs[0].font.size = DocPt(9)
    hp.runs[0].font.color.rgb = DocRGB(100, 116, 139)

    title_text = data.get("title", "تقرير تنفيذي شامل") if isinstance(data, dict) else "تقرير تنفيذي شامل"
    sub_text = data.get("subtitle", "إعداد منظومة Albaraa AI OS الذكية") if isinstance(data, dict) else ""

    # عنوان المستند الرئيسي
    tp = doc.add_paragraph()
    _set_rtl_paragraph(tp)
    tr = tp.add_run(title_text)
    tr.bold = True
    tr.font.size = DocPt(22)
    tr.font.color.rgb = DocRGB(15, 23, 42)

    if sub_text:
        sp = doc.add_paragraph()
        _set_rtl_paragraph(sp)
        sr = sp.add_run(sub_text)
        sr.font.size = DocPt(13)
        sr.font.color.rgb = DocRGB(217, 119, 6)

    doc.add_paragraph("_" * 55)

    if isinstance(data, dict) and "sections" in data:
        for sec in data["sections"]:
            h_p = doc.add_paragraph()
            _set_rtl_paragraph(h_p)
            h_run = h_p.add_run(sec.get("heading", ""))
            h_run.bold = True
            h_run.font.size = DocPt(15)
            h_run.font.color.rgb = DocRGB(30, 58, 138)

            for para in sec.get("paragraphs", []):
                p = doc.add_paragraph()
                _set_rtl_paragraph(p)
                r = p.add_run(para)
                r.font.size = DocPt(12)

            for b in sec.get("bullets", []):
                bp = doc.add_paragraph()
                _set_rtl_paragraph(bp)
                br = bp.add_run(f"• {b}")
                br.font.size = DocPt(11.5)
    else:
        for line in raw.split("\n"):
            clean = line.strip().replace("**", "").replace("#", "")
            if clean:
                p = doc.add_paragraph()
                _set_rtl_paragraph(p)
                r = p.add_run(clean)
                r.font.size = DocPt(12)

    path = "/tmp/Albaraa_Document.docx"
    doc.save(path)
    send_file(cid, path, "Albaraa_Document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"📄 {title_text}")

def make_excel(cid, msg):
    send_msg(cid, "⏳ جاري بناء وتحليل جدول البيانات (Excel)...")
    sys_prompt = (
        "أنت محلل بيانات محترف. أنشئ جدول بيانات دقيقاً وشاملاً بالعربية بناءً على طلب المستخدم. "
        "أرجع النتيجة بصيغة JSON فقط بدون أي شرح إضافي بهذا الشكل:\n"
        '{"sheet_name": "اسم الورقة", "headers": ["العمود 1", "العمود 2", "العمود 3"], "rows": [["قيمة 1", "قيمة 2", "قيمة 3"]]}'
    )
    raw = ai_ask(msg, sys_prompt)
    data = _extract_json(raw)

    wb = openpyxl.Workbook()
    ws = wb.active
    if isinstance(data, dict) and "headers" in data and "rows" in data:
        ws.title = str(data.get("sheet_name", "البيانات"))[:28]
        _style_excel_sheet(ws, data["headers"], data["rows"])
    else:
        ws.title = "البيانات"
        lines = [l for l in raw.split("\n") if "|" in l and "---" not in l]
        parsed = [[c.strip() for c in l.split("|") if c.strip()] for l in lines]
        if len(parsed) >= 2:
            _style_excel_sheet(ws, parsed[0], parsed[1:])
        else:
            _style_excel_sheet(ws, ["البيان"], [[raw[:500]]])

    path = "/tmp/Albaraa_Data.xlsx"
    wb.save(path)
    send_file(cid, path, "Albaraa_Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 ملف الإكسل المنسق جاهز")

def make_ppt(cid, msg):
    send_msg(cid, "⏳ جاري تصميم العرض التقديمي الاحترافي (PowerPoint)...")
    sys_prompt = (
        "أنت مصمم عروض تقديمية استراتيجية. صمم عرضاً تقديمياً متكاملاً من 6 شرائح باللغة العربية. "
        "أرجع النتيجة بصيغة JSON فقط بدون أي مقدمات بهذا الهيكل الدقيق:\n"
        '{"deck_title": "عنوان العرض الرئيسي", "subtitle": "وصف مختصر للعرض", '
        '"slides": [{"title": "عنوان الشريحة", "points": ["نقطة مركزة 1", "نقطة مركزة 2", "نقطة مركزة 3", "نقطة مركزة 4"]}]}'
    )
    raw = ai_ask(msg, sys_prompt)
    data = _extract_json(raw)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    NAVY = RGBColor(15, 23, 42)
    ROYAL = RGBColor(30, 58, 138)
    GOLD = RGBColor(217, 119, 6)
    WHITE = RGBColor(255, 255, 255)
    SLATE = RGBColor(51, 65, 85)
    BG_LIGHT = RGBColor(248, 250, 252)

    deck_title = data.get("deck_title", "عرض استراتيجي متكامل") if isinstance(data, dict) else "عرض تقديمي"
    deck_sub = data.get("subtitle", "منظومة Albaraa AI OS") if isinstance(data, dict) else msg[:80]
    slides_data = data.get("slides", []) if isinstance(data, dict) else []

    if not slides_data:
        slides_data = [{"title": "ملخص العرض", "points": [l.strip() for l in raw.split("\n") if l.strip()][:5]}]

    # --- الشريحة الأولى: الغلاف الملكي ---
    s0 = prs.slides.add_slide(blank_layout)
    bg0 = s0.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg0.fill.solid()
    bg0.fill.fore_color.rgb = NAVY
    bg0.line.fill.background()

    accent_bar = s0.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12.8), 0, Inches(0.533), prs.slide_height)
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = GOLD
    accent_bar.line.fill.background()


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

NAVY_HEX = "0F172A"
ROYAL_HEX = "1E3A8A"
GOLD_HEX = "D97706"
LIGHT_BG_HEX = "F8FAFC"

def _extract_json(raw: str):
    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None

def _set_rtl_paragraph(p):
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = p._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)

def _style_excel_sheet(ws, headers, rows):
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

    header = doc.sections[0].header
    hp = header.paragraphs[0]
    hp.text = f"منظومة Albaraa AI OS التنفيذية  |  التاريخ: {today_str}"
    _set_rtl_paragraph(hp)
    hp.runs[0].font.size = DocPt(9)
    hp.runs[0].font.color.rgb = DocRGB(100, 116, 139)

    title_text = data.get("title", "تقرير تنفيذي شامل") if isinstance(data, dict) else "تقرير تنفيذي شامل"
    sub_text = data.get("subtitle", "إعداد منظومة Albaraa AI OS الذكية") if isinstance(data, dict) else ""

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

def edit_uploaded_excel(cid: str, file_path: str, orig_name: str, msg: str):
    """تعديل ملف إكسل مرفوع فعليًا دون حذف أو اختصار أي صف أو عمود"""
    send_msg(cid, "⏳ جاري قراءة ملف الإكسل وتطبيق التعديلات بدقة على كافة السجلات...")
    wb = openpyxl.load_workbook(file_path)

    schema_info = []
    for sname in wb.sheetnames:
        ws = wb[sname]
        headers = [str(ws.cell(row=1, column=c).value or f"عمود_{c}") for c in range(1, ws.max_column + 1)]
        sample = [str(ws.cell(row=2, column=c).value or "") for c in range(1, ws.max_column + 1)] if ws.max_row >= 2 else []
        schema_info.append(f"ورقة '{sname}' (عدد الصفوف: {ws.max_row}): الأعمدة={headers} | مثال صف 2={sample}")

    sys_prompt = (
        "أنت مهندس بيانات Excel. لديك هيكل ملف إكسل حقيقي وتريد تنفيذ تعديلات المستخدم عليه.\n"
        "أرجع JSON فقط يحدد التعديلات المطلوبة بدقة بهذا الشكل:\n"
        '{"operations": [{"sheet": "اسم الورقة", "col_index": 4, "new_header": null, "set_all_rows_value": "ذكاء اصطناعي", "row_updates": {}}]}\n'
        "ملاحظة: col_index يبدأ من 1. إذا أراد المستخدم تغيير عمود كامل لجميع الموظفين ضع القيمة في set_all_rows_value."
    )
    raw = ai_ask(f"هيكل الملف:\n" + "\n".join(schema_info) + f"\n\nطلب التعديل:\n{msg}", sys_prompt)
    plan = _extract_json(raw)

    if isinstance(plan, dict) and plan.get("operations"):
        for op in plan["operations"]:
            sname = op.get("sheet")
            ws = wb[sname] if sname in wb.sheetnames else wb.active
            col_idx = int(op.get("col_index", 1))
            if op.get("new_header"):
                ws.cell(row=1, column=col_idx).value = op["new_header"]
            if op.get("set_all_rows_value") is not None:
                val = op["set_all_rows_value"]
                for r in range(2, ws.max_row + 1):
                    if any(ws.cell(row=r, column=c).value is not None for c in range(1, ws.max_column + 1)):
                        ws.cell(row=r, column=col_idx).value = val
            for r_str, r_val in (op.get("row_updates") or {}).items():
                ws.cell(row=int(r_str), column=col_idx).value = r_val
    clean_orig = orig_name if not orig_name.startswith("%") else "Employees_Updated.xlsx"
    out_name = f"Modified_{clean_orig}" if not clean_orig.startswith("Modified_") else clean_orig
    if not out_name.endswith(".xlsx"):
        out_name += ".xlsx"
    out_path = f"/tmp/{out_name}"
    wb.save(out_path)
    total_rows = max(0, wb.active.max_row - 1)
    send_file(cid, out_path, out_name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"✅ تم تعديل الملف بالكامل مع الحفاظ على جميع السجلات ({total_rows} سجل)")

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

    s0 = prs.slides.add_slide(blank_layout)
    bg0 = s0.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg0.fill.solid()
    bg0.fill.fore_color.rgb = NAVY
    bg0.line.fill.background()

    accent_bar = s0.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12.8), 0, Inches(0.533), prs.slide_height)
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = GOLD
    accent_bar.line.fill.background()

    tb0 = s0.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(10.8), Inches(2.0))
    tf0 = tb0.text_frame
    tf0.word_wrap = True
    p0 = tf0.paragraphs[0]
    p0.alignment = PP_ALIGN.RIGHT
    r0 = p0.add_run()
    r0.text = deck_title
    r0.font.size = Pt(40)
    r0.font.bold = True
    r0.font.color.rgb = WHITE

    tb_sub = s0.shapes.add_textbox(Inches(1.2), Inches(4.3), Inches(10.8), Inches(1.2))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    ps = tf_sub.paragraphs[0]
    ps.alignment = PP_ALIGN.RIGHT
    rs = ps.add_run()
    rs.text = f"{deck_sub}\nإعداد: منظومة Albaraa AI OS"
    rs.font.size = Pt(20)
    rs.font.color.rgb = RGBColor(251, 191, 36)

    for idx, sl_info in enumerate(slides_data, start=1):
        sl = prs.slides.add_slide(blank_layout)
        bg = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_LIGHT
        bg.line.fill.background()

        top_hdr = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.25))
        top_hdr.fill.solid()
        top_hdr.fill.fore_color.rgb = ROYAL
        top_hdr.line.fill.background()

        gold_line = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(1.25), prs.slide_width, Inches(0.08))
        gold_line.fill.solid()
        gold_line.fill.fore_color.rgb = GOLD
        gold_line.line.fill.background()

        t_box = sl.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.8))
        t_tf = t_box.text_frame
        t_tf.word_wrap = True
        tp = t_tf.paragraphs[0]
        tp.alignment = PP_ALIGN.RIGHT
        tr = tp.add_run()
        tr.text = sl_info.get("title", f"محور رقم {idx}")
        tr.font.size = Pt(26)
        tr.font.bold = True
        tr.font.color.rgb = WHITE

        card = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.7), Inches(11.7), Inches(4.9))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = RGBColor(203, 213, 225)

        c_box = sl.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(10.9), Inches(4.3))
        c_tf = c_box.text_frame
        c_tf.word_wrap = True

        for p_idx, pt_text in enumerate(sl_info.get("points", [])):
            p = c_tf.paragraphs[0] if p_idx == 0 else c_tf.add_paragraph()
            p.alignment = PP_ALIGN.RIGHT
            p.space_after = Pt(18)
            run = p.add_run()
            run.text = f"◆  {pt_text}"
            run.font.size = Pt(20)
            run.font.color.rgb = SLATE

        ftr = sl.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4))
        ftr_p = ftr.text_frame.paragraphs[0]
        ftr_p.alignment = PP_ALIGN.LEFT
        ftr_r = ftr_p.add_run()
        ftr_r.text = f"Albaraa AI OS  |  شريحة {idx}"
        ftr_r.font.size = Pt(12)
        ftr_r.font.color.rgb = RGBColor(100, 116, 139)

    path = "/tmp/Albaraa_Presentation.pptx"
    prs.save(path)
    send_file(cid, path, "Albaraa_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", f"📽️ {deck_title}")

def make_software(cid, msg):
    send_msg(cid, "⏳ جاري هندسة وبناء البرنامج وتجهيز ملفات المشروع...")
    sys_prompt = (
        "أنت مهندس برمجيات خبير (Full-Stack Architect). ابنِ برنامجاً متكاملاً ونظيفاً وجاهزاً للتشغيل بناءً على طلب المستخدم. "
        "أرجع النتيجة بصيغة JSON فقط بدون أي كلام خارجها بهذا الهيكل:\n"
        '{"project_name": "اسم_المشروع_بالانجليزية", "summary": "شرح مختصر بالعربية لكيفية التشغيل والمزايا", '
        '"files": [{"filename": "index.html", "content": "الكود الكامل هنا"}]}'
    )
    raw = ai_ask(msg, sys_prompt)
    data = _extract_json(raw)

    proj_name = "Albaraa_Project"
    summary = "تم بناء المشروع البرمجي بنجاح."
    files_list = []

    if isinstance(data, dict) and data.get("files"):
        proj_name = re.sub(r"[^a-zA-Z0-9_-]", "_", data.get("project_name", "Albaraa_Project"))[:30]
        summary = data.get("summary", summary)
        files_list = data["files"]
    else:
        files_list = [{"filename": "app.py", "content": raw}]

    if len(files_list) == 1:
        fname = files_list[0].get("filename", "program.py")
        fpath = f"/tmp/{fname}"
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(files_list[0].get("content", ""))
        send_file(cid, fpath, fname, "application/octet-stream", f"💻 تم بناء الملف البرمجي: {fname}\n\n{summary}")
    else:
        zip_name = f"{proj_name}.zip"
        zip_path = f"/tmp/{zip_name}"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in files_list:
                fn = item.get("filename", "code.txt")
                zf.writestr(fn, item.get("content", ""))
        send_file(cid, zip_path, zip_name, "application/zip", f"💻 حزمة المشروع البرمجي جاهزة: {zip_name}\n\n{summary}")


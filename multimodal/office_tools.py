import gc
import io
import os
import re
from typing import Any
import pendulum
from hijridate import Gregorian

from core.core_ai import SESSION, ai_ask, sb, send_file, send_msg
from core.event_bus import BUS

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

FONT_MAP: dict[tuple[str, ...], str] = {
    ("cairo", "كايرو"): "Cairo",
    ("tajawal", "تجول"): "Tajawal",
    ("amiri", "أميري"): "Amiri",
    ("بحث", "علمي", "أكاديمي", "اكاديمي", "دراسة", "مرجع"): "Traditional Arabic",
}

ACADEMIC_SECTIONS = [
    "الملخص التنفيذي ومشكلة البحث",
    "الإطار النظري والدراسات السابقة",
    "منهجية البحث وأدوات التحليل",
    "النتائج والمناقشة العلمية",
    "الخاتمة والتوصيات وقائمة المراجع",
]

DEFAULT_SECTIONS = [
    "الإطار العام والرؤية",
    "التحليل التشغيلي",
    "آليات التنفيذ",
    "مؤشرات القياس",
    "التوصيات الاستراتيجية",
]


def today_dates() -> str:
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ - {now.format('YYYY/MM/DD')}م"


def _cleanup_file(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def _clean_title(msg: str) -> str:
    t = ai_ask(
        msg,
        "حول الطلب إلى عنوان تقرير مؤسسي أو أكاديمي فخم من 3 إلى 7 كلمات بدون أفعال أمر. العنوان فقط:",
        mode="fast",
    ).replace('"', "").strip()[:65]

    if "تعذر" in t or len(t) < 4:
        cleaned = re.sub(r"\b(?:عطني|أعطني|اعطني|صمم|اكتب|سوي|اعمل|أريد|ابي|أبي|لوحة تحكم)\b", "", msg)
        return cleaned.strip()[:55] or "تقرير الأداء والتحليل الاستراتيجي"
    return t


def _detect_font(msg: str) -> str:
    low = msg.lower()
    return next((font for keys, font in FONT_MAP.items() if any(k in low for k in keys)), "Arial")


def _fetch_visual(query: str, out_path: str) -> str:
    try:
        en_q = ai_ask(query, "Translate this topic into 2 simple English keywords for an image search. Keywords only:", mode="fast").strip()
        clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", en_q).strip().replace(" ", ",") or "business,analytics"
        res = SESSION.get(f"https://loremflickr.com{clean_q}", timeout=10)
        if res.status_code == 200 and len(res.content) > 2000:
            with open(out_path, "wb") as f:
                f.write(res.content)
            return out_path
    except Exception:
        pass
    return ""


def _set_rtl(p: Any) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement

    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p._p.get_or_add_pPr().append(OxmlElement("w:bidi"))


def make_kpi(cid: str) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    wb.properties.creator = ""
    ws = wb.active
    ws.sheet_view.rightToLeft = True
    ws.append(["رقم العملية", "المستخدم", "القسم", "زمن التنفيذ(ث)", "الوقت الموفر(د)", "مؤشر التطور%", "المخرج"])

    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50") or []:
        ws.append([
            i.get("id"), i.get("user_role"), i.get("unit_used"),
            i.get("response_time_sec"), i.get("time_saved_min"),
            i.get("user_growth_score"), i.get("deliverable_type"),
        ])

    path = "/tmp/KPI.xlsx"
    try:
        wb.save(path)
        send_file(cid, path, "Performance_Report.xlsx", XLSX_MIME, f"📊 تقرير قياس الأداء والتطور ({today_dates()})")
        BUS.publish("office.kpi_exported", {"cid": cid})
    finally:
        _cleanup_file(path)
        del wb
        gc.collect()
def _shade_cell(cell: Any, hex_color: str) -> None:
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'))


def _styled_p(
    container: Any,
    text: str,
    font_name: str,
    size: float = 13,
    bold: bool = False,
    color: tuple[int, int, int] = (30, 41, 59),
    space_before: float = 0,
    space_after: float = 6,
) -> Any:
    from docx.shared import Pt as DocPt, RGBColor

    p = container.add_paragraph() if hasattr(container, "add_paragraph") else container
    _set_rtl(p)
    p.paragraph_format.space_before = DocPt(space_before)
    p.paragraph_format.space_after = DocPt(space_after)
    p.paragraph_format.line_spacing = 1.4
    run = p.add_run(text)
    run.font.name = font_name
    run.font.size = DocPt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)
    return p


def make_word(cid: str, msg: str) -> None:
    """توليد وتصدير مستند Word احترافي (بحث أكاديمي أو تقرير تنفيذي)."""
    from docx import Document
    from docx.shared import Inches, Pt as DocPt, RGBColor

    is_academic = any(k in msg for k in ("بحث", "علمي", "أكاديمي", "اكاديمي", "دراسة", "دراسات سابقة", "مراجع"))
    font_name = _detect_font(msg)
    send_msg(cid, "📄 جاري إعداد الوثيقة وتنسيق الجداول والصور وفق المعايير المطلوبة...")
    title = _clean_title(msg)

    if is_academic:
        sections = ACADEMIC_SECTIONS
    else:
        outline = ai_ask(msg, "ضع 5 محاور استراتيجية لتغطية هذا الموضوع بعمق تنفيذي. اكتب كل محور في سطر مستقل بدون مقدمات:", mode="arabic")
        sections = [re.sub(r"^[\-\*\#\d\.\s]+", "", s).strip() for s in outline.split("\n") if len(s.strip()) > 3][:5] or DEFAULT_SECTIONS

    doc = Document()
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.styles["Normal"].font.name = font_name
    doc.styles["Normal"].font.size = DocPt(13)
    doc.styles["Normal"].font.color.rgb = RGBColor(30, 41, 59)

    # ترويسة التقرير
    tbl_hdr = doc.add_table(rows=2, cols=1)
    tbl_hdr.autofit = False
    tbl_hdr.columns.width = DocPt(460)
    c0, c1 = tbl_hdr.cell(0, 0), tbl_hdr.cell(1, 0)
    _shade_cell(c0, "0B192C")
    _shade_cell(c1, "1E3E62")
    _styled_p(c0.paragraphs, title, font_name, size=22, bold=True, color=(255, 209, 102), space_before=8, space_after=8)
    doc_type_lbl = "دراسة بحثية علمية محكّمة" if is_academic else "تقرير تحليلي وتنفيذي شامل"
    _styled_p(c1.paragraphs, f"تاريخ الإصدار: {today_dates()}   |   {doc_type_lbl}", font_name, size=11, color=(255, 255, 255), space_before=4, space_after=4)

    # صورة الغلاف
    cover_img = _fetch_visual(title, "/tmp/word_cover.jpg")
    if cover_img and os.path.exists(cover_img):
        try:
            p_img = doc.add_paragraph()
            _set_rtl(p_img)
            p_img.add_run().add_picture(cover_img, width=Inches(6.2))
        except Exception:
            pass

    # جدول الفهرس
    doc.add_paragraph()
    tbl_idx = doc.add_table(rows=len(sections) + 1, cols=2)
    tbl_idx.style = "Table Grid"
    for col_i, hdr_txt in enumerate(("المحور / الفصل", "الرقم")):
        _shade_cell(tbl_idx.cell(0, col_i), "0B192C")
        _styled_p(tbl_idx.cell(0, col_i).paragraphs, hdr_txt, font_name, size=12, bold=True, color=(255, 209, 102), space_before=3, space_after=3)

    for i, sec in enumerate(sections, 1):
        bg = "F8FAFC" if i % 2 == 0 else "FFFFFF"
        _shade_cell(tbl_idx.cell(i, 0), bg)
        _shade_cell(tbl_idx.cell(i, 1), bg)
        _styled_p(tbl_idx.cell(i, 0).paragraphs, sec, font_name, size=12, bold=True, color=(15, 23, 42), space_before=2, space_after=2)
        _styled_p(tbl_idx.cell(i, 1).paragraphs, f"0{i}", font_name, size=12, bold=True, color=(30, 62, 98), space_before=2, space_after=2)

    sec_sys_prompt = (
        "اكتب بحثاً أكاديمياً رصيناً باللغة العربية الفصحى بأسلوب علمي موثق، مع ذكر الدراسات السابقة والمراجع العلمية بنظام APA في الفصل الأخير:"
        if is_academic else
        "اكتب تحليلاً تنفيذياً منظماً باللغة العربية الفصحى مقسماً إلى فقرات قصيرة ونقاط عملية واضحة تبدأ بـ (▪). تجنب الحشو والتكرار:"
    )

    for idx, sec in enumerate(sections, 1):
        _styled_p(doc, f"{idx}. {sec}", font_name, size=17, bold=True, color=(11, 25, 44), space_before=16, space_after=6)
        content = ai_ask(f"الموضوع الرئيسي: {title}\nالمحور الحالي: {sec}\nمتطلبات إضافية: {msg}", sec_sys_prompt, mode="arabic")
        for line in content.split("\n"):
            cl = line.strip().replace("**", "")
            if not cl:
                continue
            if cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً")):
                _styled_p(doc, cl.lstrip("# "), font_name, size=14, bold=True, color=(30, 62, 98), space_before=8, space_after=4)
            elif cl.startswith(("-", "*", "•", "▪")):
                clean_pt = re.sub(r"^[\-\*\•\▪\s]+", "", cl)
                _styled_p(doc, f"▪  {clean_pt}", font_name, size=12.5, color=(15, 23, 42), space_before=2, space_after=4)
            else:
                _styled_p(doc, cl, font_name, size=13, color=(30, 41, 59), space_before=2, space_after=6)

    if cover_img:
        _cleanup_file(cover_img)

    safe_fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "Report"
    path = f"/tmp/{safe_fname}.docx"
    try:
        doc.save(path)
        caption = f"📚 تم إعداد الدراسة العلمية الموثقة: *{title}*" if is_academic else f"📄 تم إصدار التقرير التنفيذي المنسّق: *{title}*"
        send_file(cid, path, f"{safe_fname}.docx", DOCX_MIME, caption)
        BUS.publish("office.word_exported", {"cid": cid, "title": title})
    finally:
        _cleanup_file(path)
        del doc
        gc.collect()


def _parse_pipe_table(raw: str, max_cols: int = 6) -> list[list[Any]]:
    """تحويل الجدول النصي المفصول بـ | إلى مصفوفة بيانات مع تحويل الأرقام تلقائياً."""
    parsed: list[list[Any]] = []
    for line in raw.split("\n"):
        if "|" not in line or set(line.replace("|", "").strip()).issubset({"-", ":", " "}):
            continue
        vals: list[Any] = []
        for item in line.split("|"):
            v = item.strip().replace("**", "")
            if v and len(vals) < max_cols:
                try:
                    v = float(v) if "." in v else int(v)
                except ValueError:
                    pass
                vals.append(v)
        if len(vals) >= 5:
            parsed.append(vals)
    return parsed
def _render_excel_chart(labels: list[str], actuals: list[float], targets: list[float], out_img: str) -> bool:
    """رسم مقارنة الأداء المحقق مقابل المستهدف بصيغة PNG عالية الدقة."""
    import arabic_reshaper
    from bidi.algorithm import get_display
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def _ar(txt: str) -> str:
        return get_display(arabic_reshaper.reshape(str(txt)), base_dir="R")

    try:
        fig, ax = plt.subplots(figsize=(10.5, 4.3), dpi=130)
        fig.patch.set_facecolor("#0B192C")
        ax.set_facecolor("#132743")
        x_pos = range(len(labels))
        bars = ax.bar([p - 0.18 for p in x_pos], actuals, width=0.35, label=_ar("المحقق الفعلي"), color="#00B4D8")
        ax.bar([p + 0.18 for p in x_pos], targets, width=0.35, label=_ar("المستهدف المخطط"), color="#FFD166")

        ax.set_xticks(list(x_pos))
        ax.set_xticklabels([_ar(lbl) for lbl in labels])
        ax.set_title(_ar("مقارنة الأداء المحقق مقابل المستهدف"), color="#FFD166", fontsize=14, fontweight="bold", pad=12)
        ax.tick_params(colors="white", labelsize=10)
        ax.legend(facecolor="#0B192C", edgecolor="none", labelcolor="white", fontsize=10)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for bar in bars:
            yv = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, yv + 1, str(yv), ha="center", va="bottom", color="#00B4D8", fontsize=9, fontweight="bold")

        plt.tight_layout()
        plt.savefig(out_img, facecolor="#0B192C")
        plt.close(fig)
        return os.path.exists(out_img)
    except Exception as exc:
        print(f"Chart Img Err: {exc}", flush=True)
        return False


def make_excel(cid: str, msg: str) -> None:
    """توليد مصنف Excel تنفيذي يضم لوحة القيادة، بطاقات المؤشرات، الرسم البياني، وسجل البيانات."""
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    send_msg(cid, "📊 جاري إعداد ملف الإكسل ولوحة المؤشرات والرسوم البيانية...")
    prompt = (
        "أنت محلل بيانات وخبير تصميم لوحات قيادة Excel. أنشئ 3 أقسام مفصولة بسطر === فقط:\n"
        "1: عنوان رسمي للتقرير (3 إلى 6 كلمات بدون أفعال أمر).\n"
        "2: جدول بيانات من 9 صفوف (صف عناوين + 8 صفوف بيانات واقعية) بـ 6 أعمدة مفصولة بـ | فقط:\n"
        "الاسم أو البند | المسمى الوظيفي | الإدارة | المحقق الفعلي (رقم 75-115) | المستهدف (رقم 85-100) | الإجراء التطويري\n"
        "3: ملخص تنفيذي من 3 توصيات استراتيجية بدون رموز نجمية.\n"
        "التزم بالفصل بـ === بدون مقدمات."
    )
    res = ai_ask(msg, prompt, mode="fast")
    parts = [p.strip() for p in res.split("===") if p.strip()]
    p1, p2, p3 = (parts + ["", "", ""])[:3]

    title = p1.replace('"', "").strip()[:55] if (p1 and len(p1) < 85 and "|" not in p1) else "تقرير تقييم الأداء والكفاءة"
    raw = p2 if "|" in p2 else res
    summary = p3 or "1. تعزيز برامج التطوير المهني للوحدات دون المستهدف.\n2. ربط الحوافز الفصلية بمؤشرات الإنجاز الفعلية.\n3. تعميم أفضل الممارسات التشغيلية."

    parsed = _parse_pipe_table(raw)
    if len(parsed) < 2:
        parsed = [
            ["الاسم", "المسمى", "الإدارة", "المحقق", "المستهدف", "الإجراء"],
            ["سارة القحطاني", "أخصائي أول", "الموارد البشرية", 98, 90, "ترشيح للقيادة"],
            ["عبدالله العتيبي", "مهندس مشاريع", "العمليات", 92, 95, "تحسين الجدولة"],
            ["نورة الشمري", "محلل مالي", "المالية", 104, 100, "تعميم النموذج"],
        ]

    wb = openpyxl.Workbook()
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    ws_dash = wb.active
    ws_dash.title = "لوحة القيادة"
    ws_dash.sheet_view.rightToLeft = True
    ws_dash.sheet_view.showGridLines = False

    ws_data = wb.create_sheet("سجل البيانات والتحليل")
    ws_data.sheet_view.rightToLeft = True

    fill = lambda hx: PatternFill(start_color=hx, end_color=hx, fill_type="solid")
    f_navy, f_slate, f_white, f_zebra = fill("0B192C"), fill("1E3E62"), fill("FFFFFF"), fill("F8FAFC")
    f_green, f_blue, f_amber = fill("DCFCE7"), fill("DBEAFE"), fill("FEF3C7")
    thin = Side(style="thin", color="CBD5E1")
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)
    aln_c = Alignment(horizontal="center", vertical="center", wrap_text=True)
    aln_r = Alignment(horizontal="right", vertical="center", wrap_text=True)

    headers = ["الرقم المرجعي", "الاسم / البند", "التصنيف / المسمى", "القسم / الإدارة", "المحقق الفعلي", "المستهدف", "الإنجاز %", "الفارق", "التقييم المعتمد", "خطة التطوير"]
    ws_data.row_dimensions.height = 32
    for c_i, h in enumerate(headers, 1):
        cell = ws_data.cell(1, c_i, h)
        cell.fill, cell.font, cell.alignment, cell.border = f_navy, Font(color="FFD166", size=11, bold=True), aln_c, brd

    rows = parsed[1:]
    last_r = len(rows) + 1
    chart_labels, chart_act, chart_tgt = [], [], []
    sum_pct, pass_cnt = 0.0, 0

    for idx, r in enumerate(rows, 2):
        ws_data.row_dimensions[idx].height = 26
        padded = (r + ["بند", "أخصائي", "العمليات", 88, 90, "متابعة دورية"])[:6]
        nm, role_t, dp, raw_ac, raw_tg, act_plan = padded
        ac = raw_ac if isinstance(raw_ac, (int, float)) else 88
        tg = raw_tg if isinstance(raw_tg, (int, float)) else 90
        pct = round((ac / max(tg, 1)) * 100, 1)

        eval_txt = "متفوق 🌟" if pct >= 100 else ("جيد جداً ✅" if pct >= 85 else "يحتاج تطوير ⚠️")
        sum_pct += pct
        if pct >= 85:
            pass_cnt += 1
        if len(chart_labels) < 7:
            chart_labels.append(str(nm)[:13])
            chart_act.append(ac)
            chart_tgt.append(tg)

        entries = [f"REF-{100 + idx}", nm, role_t, dp, ac, tg, f'=ROUND((E{idx}/MAX(F{idx},1))*100,1)&"%"', f"=ROUND(E{idx}-F{idx},1)", eval_txt, act_plan]
        for c_i, val in enumerate(entries, 1):
            cell = ws_data.cell(idx, c_i, val)
            cell.border = brd
            cell.font = Font(color="0F172A", size=11, bold=(c_i in (1, 2, 7, 9)))
            cell.alignment = aln_c if c_i in (1, 5, 6, 7, 8, 9) else aln_r
            if idx % 2 == 0:
                cell.fill = f_zebra
            if c_i == 9:
                cell.fill = f_green if pct >= 100 else (f_blue if pct >= 85 else f_amber)

    cnt = max(len(rows), 1)
    avg_pct = round(sum_pct / cnt, 1)
    tot_r = last_r + 1
    ws_data.row_dimensions[tot_r].height = 30
    tots = ["الإجمالي", f"{cnt} سجل", "كافة الفئات", "جميع الإدارات", f"=SUM(E2:E{last_r})", f"=SUM(F2:F{last_r})", f"{avg_pct}%", f"=SUM(H2:H{last_r})", f"{pass_cnt} محقق", "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        cell = ws_data.cell(tot_r, c_i, val)
        cell.fill, cell.font, cell.alignment, cell.border = f_slate, Font(color="FFFFFF", size=11, bold=True), aln_c, brd

    for c_i in range(1, 11):
        ws_data.column_dimensions[get_column_letter(c_i)].width = 25 if c_i in (2, 10) else (19 if c_i in (3, 4, 9) else 15)
    for c_i in range(1, 14):
        ws_dash.column_dimensions[get_column_letter(c_i)].width = 14

    ws_dash.merge_cells("B2:M3")
    ws_dash["B2"] = f"لوحة القيادة التنفيذية: {title}"
    ws_dash["B2"].fill, ws_dash["B2"].font, ws_dash["B2"].alignment = f_navy, Font(color="FFD166", size=18, bold=True), aln_c

    ws_dash.merge_cells("B4:M4")
    ws_dash["B4"] = f"تاريخ الإصدار: {today_dates()}  |  بطاقة الأداء المتوازن والمؤشرات التشغيلية"
    ws_dash["B4"].fill, ws_dash["B4"].font, ws_dash["B4"].alignment = f_slate, Font(color="FFFFFF", size=11), aln_c

    cards = [
        ("B", "D", "إجمالي الأداء المحقق", f"=SUM('سجل البيانات والتحليل'!E2:E{last_r})", "1E3A8A"),
        ("E", "G", "متوسط نسبة الإنجاز", f"{avg_pct}%", "0F766E"),
        ("H", "J", "الفارق عن المستهدف", f"=SUM('سجل البيانات والتحليل'!H2:H{last_r})", "B45309"),
        ("K", "M", "نسبة المحققين للمعيار", f"{round((pass_cnt / cnt) * 100)}%", "4338CA"),
    ]
    ws_dash.row_dimensions.height, ws_dash.row_dimensions.height = 26, 40
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6")
        ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value, ws_dash[f"{cs}6"].fill = tk, fill(hx)
        ws_dash[f"{cs}6"].font, ws_dash[f"{cs}6"].alignment = Font(color="FFFFFF", size=11, bold=True), aln_c
        ws_dash[f"{cs}7"].value, ws_dash[f"{cs}7"].fill = fk, f_white
        ws_dash[f"{cs}7"].font, ws_dash[f"{cs}7"].alignment, ws_dash[f"{cs}7"].border = Font(color=hx, size=18, bold=True), aln_c, brd

    for r_idx in range(9, 27):
        ws_dash.row_dimensions[r_idx].height = 20

    chart_img = "/tmp/dash_chart.png"
    if _render_excel_chart(chart_labels, chart_act, chart_tgt, chart_img):
        img_xl = XLImage(chart_img)
        img_xl.width, img_xl.height = 820, 330
        ws_dash.add_image(img_xl, "B9")

    clean_sum = summary.replace("**", "").replace("###", "").replace("##", "").strip()
    ws_dash.merge_cells("B27:M27")
    ws_dash["B27"] = "💡 القراءة التحليلية والتوصيات التنفيذية"
    ws_dash["B27"].fill, ws_dash["B27"].font, ws_dash["B27"].alignment = f_navy, Font(color="FFD166", size=12, bold=True), aln_r

    ws_dash.row_dimensions.height = 28
    ws_dash.merge_cells("B28:M33")
    ws_dash["B28"] = clean_sum
    ws_dash["B28"].fill, ws_dash["B28"].font, ws_dash["B28"].border = f_white, Font(color="1E293B", size=11), brd
    ws_dash["B28"].alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)

    safe_fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "Dashboard"
    path = f"/tmp/{safe_fname}.xlsx"
    try:
        wb.save(path)
        send_file(cid, path, f"{safe_fname}.xlsx", XLSX_MIME, f"📊 تم إعداد لوحة القيادة: *{title}*\n✨ تشمل: بطاقات المؤشرات التفاعلية + سجل البيانات وخطة التطوير.")
        BUS.publish("office.excel_exported", {"cid": cid, "title": title})
        if os.path.exists(chart_img):
def make_pptx(cid: str, msg: str) -> None:
    """توليد وتصدير عرض تقديمي PowerPoint احترافي بالهوية البصرية والصور."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt
    from core.core_ai import ai_ask_json

    font_name = _detect_font(msg)
    send_msg(cid, "📊 جاري تصميم العرض التقديمي وتنسيق الشرائح والصور...")
    title = _clean_title(msg)

    prompt = (
        f"أنت خبير تصميم عروض تقديمية تنفيذية. أنشئ محتوى عرض تقديمي احترافي حول: {msg}\n"
        'أرجع JSON فقط: {"subtitle": "وصف مختصر", "slides": [{"heading": "عنوان الشريحة", "points": ["نقطة 1", "نقطة 2", "نقطة 3", "نقطة 4"]}]}\n'
        "أنشئ 6 شرائح متنوعة باللغة العربية الفصحى."
    )
    data = ai_ask_json(prompt, "أنت مصمم عروض تقديمية تنفيذية باللغة العربية الفصحى.", mode="arabic")
    if not isinstance(data, dict) or not data.get("slides"):
        data = {
            "subtitle": "عرض تحليلي واستراتيجي شامل",
            "slides": [{"heading": "نظرة عامة", "points": ["تحديد الأهداف الاستراتيجية", "تحليل الوضع الراهن", "رفع كفاءة الأداء"]}],
        }

    prs = Presentation()
    prs.core_properties.author = ""
    prs.core_properties.last_modified_by = ""
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts

    NAVY, SLATE = RGBColor(11, 25, 44), RGBColor(30, 62, 98)
    GOLD, WHITE = RGBColor(255, 209, 102), RGBColor(255, 255, 255)
    LIGHT_BG, DARK_TXT = RGBColor(248, 250, 252), RGBColor(15, 23, 42)

    def _add_p(tf: Any, txt: str, sz: int, clr: RGBColor, bold: bool = False, align: Any = PP_ALIGN.RIGHT, sp: int = 0, first: bool = False) -> None:
        p = tf.paragraphs if first else tf.add_paragraph()
        p.text, p.alignment, p.font.name, p.font.size, p.font.bold, p.font.color.rgb = txt, align, font_name, Pt(sz), bold, clr
        if sp:
            p.space_before = Pt(sp)

    # شريحة الغلاف
    s0 = prs.slides.add_slide(blank)
    s0.background.fill.solid()
    s0.background.fill.fore_color.rgb = NAVY
    bar = s0.shapes.add_shape(1, Inches(0), Inches(6.8), Inches(13.333), Inches(0.2))
    bar.fill.solid()
    bar.fill.fore_color.rgb = GOLD
    bar.line.fill.background()

    tf0 = s0.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(2)).text_frame
    tf0.word_wrap = True
    _add_p(tf0, title, 40, GOLD, bold=True, first=True)
    _add_p(tf0, data.get("subtitle", ""), 20, WHITE, sp=14)
    _add_p(tf0, f"تاريخ الإصدار: {today_dates()}", 14, RGBColor(148, 163, 184), sp=28)

    slide_img = _fetch_visual(title, "/tmp/ppt_cover.jpg")
    if slide_img and os.path.exists(slide_img):
        try:
            s0.shapes.add_picture(slide_img, Inches(0.8), Inches(4.5), width=Inches(3.2))
        except Exception:
            pass

    # شرائح المحتوى
    for idx, sl in enumerate(data.get("slides", [])[:8], 1):
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = LIGHT_BG

        hdr = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = NAVY
        hdr.line.fill.background()

        accent = slide.shapes.add_shape(1, Inches(0), Inches(1.2), Inches(13.333), Inches(0.08))
        accent.fill.solid()
        accent.fill.fore_color.rgb = GOLD
        accent.line.fill.background()

        htf = slide.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.7)).text_frame
        _add_p(htf, f"{idx}. {sl.get('heading', '')}", 26, GOLD, bold=True, first=True)

        btf = slide.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.8)).text_frame
        btf.word_wrap = True
        for p_i, pt_text in enumerate(sl.get("points", [])):
            _add_p(btf, f"▪ {pt_text}", 20, DARK_TXT, first=(p_i == 0))
            btf.paragraphs[p_i].space_after = Pt(16)

        ftf = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4)).text_frame
        _add_p(ftf, f"{title}  |  شريحة {idx}", 11, SLATE, align=PP_ALIGN.LEFT, first=True)

    if slide_img:
        _cleanup_file(slide_img)

    safe_fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "Presentation"
    path = f"/tmp/{safe_fname}.pptx"
    try:
        prs.save(path)
        send_file(cid, path, f"{safe_fname}.pptx", PPTX_MIME, f"📽️ تم تصميم العرض التقديمي: *{title}*")
        BUS.publish("office.pptx_exported", {"cid": cid, "title": title})
    finally:
        _cleanup_file(path)
        del prs
        gc.collect()
def make_live_powerbi(cid: str, msg: str) -> None:
    """إنشاء لوحة قيادة تفاعلية حية وإرسال رابطها للتعديل المباشر."""
    import json
    from core.config import RENDER_URL
    from core.core_ai import ai_ask_json

    send_msg(cid, "📊 جاري بناء لوحة القيادة التفاعلية الحية وتجهيز رابط التعديل المباشر...")
    title = _clean_title(msg)
    prompt = (
        f"أنشئ بيانات لوحة قيادة احترافية حول: {msg}\n"
        'أرجع JSON فقط بهذا الهيكل الدقيق:\n'
        '{"title": "عنوان اللوحة", "cols": ["البند", "القسم", "المحقق", "المستهدف", "الحالة"], '
        '"rows": [["بند 1", "قسم 1", "95", "100", "ممتاز"], ["بند 2", "قسم 2", "88", "90", "جيد"]]}'
    )
    board = ai_ask_json(prompt, "أنت محلل بيانات محترف. أنشئ 6 صفوف بيانات واقعية وأرقام دقيقة.", mode="fast")
    if not isinstance(board, dict) or not board.get("rows"):
        board = {
            "title": title,
            "cols": ["البند", "القسم", "المحقق", "المستهدف", "الحالة"],
            "rows": [
                ["مؤشر الإنجاز العام", "العمليات", "94", "95", "ممتاز"],
                ["جودة المخرجات", "الجودة", "98", "95", "متفوق"],
                ["سرعة الاستجابة", "التقنية", "91", "90", "ممتاز"],
            ],
        }

    saved = sb("POST", "self_learning_logs", {"user_role": "live_board", "lesson_learned": json.dumps(board, ensure_ascii=False), "is_active": True})
    bid = saved[0].get("id", 1) if isinstance(saved, list) and saved else 1
    board_link = f"{RENDER_URL}/board/{bid}" if RENDER_URL else f"/board/{bid}"
    send_msg(cid, f"📊 *تم إطلاق لوحة القيادة الحية بنجاح:*\n*{board.get('title', title)}*\n\n🔗 *رابط اللوحة التفاعلية للتعديل المباشر:*\n{board_link}")
    BUS.publish("office.live_board_created", {"cid": cid, "board_id": bid})


def make_powerbi_kit(cid: str, msg: str) -> None:
    """توليد وتصدير دليل هندسة Power BI ومعادلات DAX بصيغة Word."""
    from docx import Document
    from docx.shared import Pt as DocPt

    font_name = _detect_font(msg)
    send_msg(cid, "📈 جاري إعداد نموذج البيانات ومعادلات DAX الاحترافية...")
    title = _clean_title(msg)
    prompt = (
        f"أنت خبير Power BI ومهندس ذكاء أعمال (BI Architect). للمشروع التالي: {msg}\n"
        "أعدّ وثيقة هندسية تنفيذية تشمل:\n"
        "1. هيكل الجداول المقترح (Fact & Dimension Tables) وأعمدة كل جدول.\n"
        "2. 6 معادلات DAX احترافية مكتوبة بدقة وجاهزة للنسخ المباشر داخل Power BI لحساب المؤشرات (KPIs).\n"
        "3. تصميم لوحة القيادة (Dashboard Layout) وتوزيع البطاقات والرسوم البيانية في كل صفحة."
    )
    guide = ai_ask(msg, prompt, temperature=0.2, mode="arabic")

    doc = Document()
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.styles["Normal"].font.name = font_name
    doc.styles["Normal"].font.size = DocPt(13)

    tbl = doc.add_table(rows=1, cols=1)
    cell = tbl.cell(0, 0)
    _shade_cell(cell, "0B192C")
    _styled_p(cell.paragraphs[0], f"دليل هندسة Power BI: {title}", font_name, size=18, bold=True, color=(255, 209, 102), space_before=4, space_after=2)
    _styled_p(cell, f"تاريخ الإصدار: {today_dates()}", font_name, size=11, color=(255, 255, 255), space_before=0, space_after=4)

    for line in guide.split("\n"):
        cl = line.strip().replace("**", "")
        if not cl:
            continue
        is_heading = cl.startswith(("#", "1.", "2.", "3."))
        _styled_p(
            doc,
            cl.lstrip("# "),
            font_name,
            size=15 if is_heading else 12.5,
            bold=is_heading,
            color=(11, 25, 44) if is_heading else (30, 41, 59),
            space_before=6 if is_heading else 2,
            space_after=4,
        )

    safe_fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "PowerBI_Guide"
    path = f"/tmp/{safe_fname}.docx"
    try:
        doc.save(path)
        send_file(cid, path, f"{safe_fname}.docx", DOCX_MIME, f"📈 تم إعداد حزمة هندسة Power BI ومعادلات DAX: *{title}*")
        BUS.publish("office.powerbi_exported", {"cid": cid, "title": title})
    finally:
        _cleanup_file(path)
        del doc
        gc.collect()

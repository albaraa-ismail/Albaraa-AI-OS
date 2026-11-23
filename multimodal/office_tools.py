import gc
import os
import re
import uuid
from typing import Any
import pendulum
from hijridate import Gregorian
from core.config import RENDER_URL
from core.core_ai import SESSION, ai_ask, ai_ask_json, sb
from core.event_bus import BUS
from core.orchestrator import send_msg
from multimodal.pro_capabilities import send_file

MIME = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def today_dates() -> str:
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ - {now.format('YYYY/MM/DD')}م"


def _clean_title(msg: str) -> str:
    t = ai_ask(msg, "حول الطلب إلى عنوان تقرير مؤسسي فخم من 3 إلى 7 كلمات بدون أفعال أمر. العنوان فقط:", mode="fast").replace('"', "").strip()[:65]
    if "تعذر" in t or len(t) < 4:
        t = re.sub(r"\b(?:عطني|أعطني|اعطني|صمم|اكتب|سوي|اعمل|أريد|ابي|أبي|لوحة تحكم)\b", "", msg).strip()[:55]
    return t or "تقرير الأداء والتحليل الاستراتيجي"


def _detect_font(msg: str) -> str:
    low = msg.lower()
    for keys, font in [(("cairo", "كايرو"), "Cairo"), (("tajawal", "تجول"), "Tajawal"), (("amiri", "أميري"), "Amiri"), (("بحث", "علمي", "أكاديمي", "دراسة"), "Traditional Arabic")]:
        if any(k in low for k in keys):
            return font
    return "Arial"


def _fetch_visual(query: str, out_path: str) -> str:
    try:
        en_q = ai_ask(query, "2 simple English keywords for image search. Keywords only:", mode="fast").strip()
        clean_q = re.sub(r"[^a-zA-Z0-9\s]", "", en_q).strip().replace(" ", ",") or "business,analytics"
                img_url = "https" + ":" + "//" + "://loremflickr.com" + clean_q
        r = SESSION.get(img_url, timeout=10)
        if r.status_code == 200 and len(r.content) > 2000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
    except Exception:
        pass
    return ""


def _drop(*paths: str) -> None:
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def make_kpi(cid: str) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.sheet_view.rightToLeft = True
    ws.append(["المعرف", "الدور", "الوحدة", "زمن الاستجابة (ث)", "الوقت الموفر (د)", "مؤشر الجودة %", "نوع المخرج"])
    for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50") or []:
        if isinstance(i, dict):
            ws.append([i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")])
    path = f"/tmp/KPI_{uuid.uuid4().hex[:6]}.xlsx"
    wb.save(path)
    send_file(cid, path, "Performance_Report.xlsx", MIME["xlsx"], f"📊 تقرير قياس الأداء والتطور ({today_dates()})")
    BUS.publish("office.kpi_exported", {"cid": cid})
    _drop(path)
    del wb
    gc.collect()


def _build_word_doc(
    cid: str,
    title: str,
    subtitle: str,
    sections: list[tuple[str, str]],
    font_name: str,
    caption: str,
    event: str,
    with_cover: bool = True,
) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import nsdecls
    from docx.shared import Inches, Pt, RGBColor

    doc = Document()
    doc.styles["Normal"].font.name = font_name
    doc.styles["Normal"].font.size = Pt(12.5)

    def _add(target: Any, text: str, size: float, bold: bool, rgb: tuple[int, int, int], sb_pt: float = 4, sa_pt: float = 4) -> None:
        p = target.add_paragraph() if hasattr(target, "add_paragraph") else target
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
        p.paragraph_format.space_before = Pt(sb_pt)
        p.paragraph_format.space_after = Pt(sa_pt)
        run = p.add_run(text)
        run.font.name = font_name
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor(*rgb)
    cover = ""
    if with_cover:
        tbl_cov = doc.add_table(rows=1, cols=1)
        c0 = tbl_cov.cell(0, 0)
        c0._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="0B192C"/>'))
        _add(next(iter(c0.paragraphs)), title, 22, True, (255, 209, 102), 8, 4)
        _add(c0, f"{subtitle}  |  {today_dates()}", 12, False, (255, 255, 255), 2, 8)
        cover = _fetch_visual(title, f"/tmp/cov_{uuid.uuid4().hex[:6]}.jpg")
        if cover:
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.add_run().add_picture(cover, width=Inches(5.8))

    if len(sections) > 1:
        doc.add_paragraph()
        tbl_idx = doc.add_table(rows=len(sections) + 1, cols=2)
        tbl_idx.style = "Table Grid"
        for ci, h in enumerate(("المحور / الفصل", "الرقم")):
            tbl_idx.cell(0, ci)._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="0B192C"/>'))
            _add(next(iter(tbl_idx.cell(0, ci).paragraphs)), h, 12, True, (255, 209, 102), 2, 2)
        for i, (st, _) in enumerate(sections, 1):
            bg = "F8FAFC" if i % 2 == 0 else "FFFFFF"
            for ci, val in enumerate((st, f"0{i}")):
                tbl_idx.cell(i, ci)._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>'))
                _add(next(iter(tbl_idx.cell(i, ci).paragraphs)), val, 12, True, (15, 23, 42) if ci == 0 else (30, 62, 98), 2, 2)

    for idx, (sec_title, body) in enumerate(sections, 1):
        _add(doc, f"{idx}. {sec_title}", 16, True, (11, 25, 44), 14, 6)
        for line in body.split("\n"):
            cl = line.strip().replace("**", "")
            if not cl:
                continue
            is_h = cl.startswith(("#", "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً"))
            txt = f"▪  {re.sub(r'^[\-\*\•\▪\s]+', '', cl)}" if cl.startswith(("-", "*", "•", "▪")) else cl.lstrip("# ")
            _add(doc, txt, 14 if is_h else 12.5, is_h, (30, 62, 98) if is_h else (30, 41, 59), 6 if is_h else 2, 4)

    fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "Document"
    path = f"/tmp/{fname}_{uuid.uuid4().hex[:6]}.docx"
    doc.save(path)
    send_file(cid, path, f"{fname}.docx", MIME["docx"], caption)
    BUS.publish(event, {"cid": cid, "title": title})
    _drop(path, cover)
    del doc
    gc.collect()


def make_word(cid: str, msg: str) -> None:
    is_ac = any(k in msg for k in ("بحث", "علمي", "أكاديمي", "اكاديمي", "دراسة", "مراجع"))
    send_msg(cid, "📄 جاري إعداد الوثيقة وتنسيق الجداول والصور...")
    title = _clean_title(msg)
    if is_ac:
        heads = ["الملخص التنفيذي ومشكلة البحث", "الإطار النظري والدراسات السابقة", "منهجية البحث", "النتائج والمناقشة", "الخاتمة والمراجع"]
        sys_p = "اكتب بحثا أكاديميا رصينا بالعربية الفصحى مع ذكر الدراسات السابقة والمراجع بنظام APA:"
    else:
        out = ai_ask(msg, "ضع 5 محاور استراتيجية لتغطية الموضوع. كل محور في سطر بدون مقدمات:", mode="arabic")
        heads = [re.sub(r"^[\-\*\#\d\.\s]+", "", s).strip() for s in out.split("\n") if len(s.strip()) > 3][:5] or ["الإطار العام", "التحليل", "التنفيذ", "المؤشرات", "التوصيات"]
        sys_p = "اكتب تحليلا تنفيذيا منظما بالعربية الفصحى في نقاط واضحة تبدأ بـ (▪):"
    sections = [(h, ai_ask(f"الموضوع: {title}\nالمحور: {h}\nالتفاصيل: {msg}", sys_p, mode="arabic")) for h in heads]
    _build_word_doc(cid, title, "دراسة علمية محكمة" if is_ac else "تقرير تحليلي وتنفيذي", sections, _detect_font(msg), f"📄 تم إصدار الوثيقة: *{title}*", "office.word_exported", with_cover=True)


def make_excel(cid: str, msg: str) -> None:
    import openpyxl
    import arabic_reshaper
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from bidi.algorithm import get_display

    _ar = lambda txt: get_display(arabic_reshaper.reshape(str(txt)), base_dir="R")
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
    p1, p2, p3 = ([p.strip() for p in res.split("===") if p.strip()] + ["", "", ""])[:3]
    title = p1.replace('"', "").strip()[:55] if (p1 and len(p1) < 85 and "|" not in p1) else "تقرير تقييم الأداء والكفاءة"
    summary = p3 or "1. تعزيز برامج التطوير المهني للوحدات دون المستهدف.\n2. ربط الحوافز الفصلية بمؤشرات الإنجاز الفعلية.\n3. تعميم أفضل الممارسات التشغيلية."

    wb = openpyxl.Workbook()
    ws_dash = wb.active
    ws_dash.title = "لوحة القيادة"
    ws_dash.sheet_view.rightToLeft = True
    ws_dash.sheet_view.showGridLines = False
    ws_data = wb.create_sheet("سجل البيانات والتحليل")
    ws_data.sheet_view.rightToLeft = True

    _fill = lambda hx: PatternFill(start_color=hx, end_color=hx, fill_type="solid")
    f_navy, f_slate, f_white, f_zebra = _fill("0B192C"), _fill("1E3E62"), _fill("FFFFFF"), _fill("F8FAFC")
    f_green, f_blue, f_amber = _fill("DCFCE7"), _fill("DBEAFE"), _fill("FEF3C7")
    s_thin = Side(style="thin", color="CBD5E1")
    brd = Border(left=s_thin, right=s_thin, top=s_thin, bottom=s_thin)
    aln_c = Alignment(horizontal="center", vertical="center", wrap_text=True)
    aln_r = Alignment(horizontal="right", vertical="center", wrap_text=True)
    parsed = []
    for l in (p2 if "|" in p2 else res).split("\n"):
        if "|" in l and not set(l.replace("|", "").strip()).issubset({"-", ":", " "}):
            vals = []
            for x in l.split("|"):
                v = x.strip().replace("**", "")
                if v and len(vals) < 6:
                    try:
                        v = float(v) if "." in v else int(v)
                    except ValueError:
                        pass
                    vals.append(v)
            if len(vals) >= 5:
                parsed.append(vals)

    if len(parsed) < 2:
        parsed = [
            ["البند", "المسمى", "الإدارة", "المحقق", "المستهدف", "الإجراء"],
            ["سارة القحطاني", "أخصائي أول", "الموارد البشرية", 98, 90, "ترشيح للقيادة"],
            ["عبدالله العتيبي", "مهندس مشاريع", "العمليات", 92, 95, "تحسين الجدولة"],
            ["نورة الشمري", "محلل مالي", "المالية", 104, 100, "تعميم النموذج"],
        ]

    headers = ["الرقم المرجعي", "الاسم / البند", "التصنيف / المسمى", "القسم / الإدارة", "المحقق الفعلي", "المستهدف", "الإنجاز %", "الفارق", "التقييم المعتمد", "خطة التطوير"]
    ws_data.row_dimensions[1].height = 32
    for c_i, h in enumerate(headers, 1):
        c = ws_data.cell(1, c_i, h)
        c.fill, c.font, c.alignment, c.border = f_navy, Font(color="FFD166", size=11, bold=True), aln_c, brd

    rows = parsed[1:]
    last_r = len(rows) + 1
    chart_labels, chart_act, chart_tgt, sum_pct, pass_cnt = [], [], [], 0.0, 0

    for idx, r in enumerate(rows, 2):
        ws_data.row_dimensions[idx].height = 26
        nm, role_t, dp, raw_ac, raw_tg, act_plan = (r + ["بند", "أخصائي", "العمليات", 88, 90, "متابعة دورية"])[:6]
        ac = raw_ac if isinstance(raw_ac, (int, float)) else 88
        tg = raw_tg if isinstance(raw_tg, (int, float)) else 90
        pct = round((ac / max(tg, 1)) * 100, 1)
        sum_pct += pct
        pass_cnt += int(pct >= 85)
        eval_txt = "متفوق 🌟" if pct >= 100 else ("جيد جداً ✅" if pct >= 85 else "يحتاج تطوير ⚠️")
        if len(chart_labels) < 7:
            chart_labels.append(_ar(str(nm)[:13]))
            chart_act.append(ac)
            chart_tgt.append(tg)

        entries = [f"REF-{100+idx}", nm, role_t, dp, ac, tg, f'=ROUND((E{idx}/MAX(F{idx},1))*100,1)&"%"', f"=ROUND(E{idx}-F{idx},1)", eval_txt, act_plan]
        for c_i, val in enumerate(entries, 1):
            c = ws_data.cell(idx, c_i, val)
            c.border = brd
            c.font = Font(color="0F172A", size=11, bold=(c_i in (1, 2, 7, 9)))
            c.alignment = aln_c if c_i in (1, 5, 6, 7, 8, 9) else aln_r
            if idx % 2 == 0:
                c.fill = f_zebra
            if c_i == 9:
                c.fill = f_green if pct >= 100 else (f_blue if pct >= 85 else f_amber)

    cnt = max(len(rows), 1)
    avg_pct = round(sum_pct / cnt, 1)
    tot_r = last_r + 1
    ws_data.row_dimensions[tot_r].height = 30
    tots = ["الإجمالي", f"{cnt} سجل", "كافة الفئات", "جميع الإدارات", f"=SUM(E2:E{last_r})", f"=SUM(F2:F{last_r})", f"{avg_pct}%", f"=SUM(H2:H{last_r})", f"{pass_cnt} محقق", "المؤشر العام"]
    for c_i, val in enumerate(tots, 1):
        c = ws_data.cell(tot_r, c_i, val)
        c.fill, c.font, c.alignment, c.border = f_slate, Font(color="FFFFFF", size=11, bold=True), aln_c, brd

    for c_i in range(1, 11):
        ws_data.column_dimensions[get_column_letter(c_i)].width = 25 if c_i in (2, 10) else (19 if c_i in (3, 4, 9) else 15)
    for c in range(1, 14):
        ws_dash.column_dimensions[get_column_letter(c)].width = 14

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
        ("K", "M", "نسبة المحققين للمعيار", f"{round((pass_cnt/cnt)*100)}%", "4338CA"),
    ]
    ws_dash.row_dimensions[6].height, ws_dash.row_dimensions[7].height = 26, 40
    for cs, ce, tk, fk, hx in cards:
        ws_dash.merge_cells(f"{cs}6:{ce}6")
        ws_dash.merge_cells(f"{cs}7:{ce}7")
        ws_dash[f"{cs}6"].value, ws_dash[f"{cs}6"].fill, ws_dash[f"{cs}6"].font, ws_dash[f"{cs}6"].alignment = tk, _fill(hx), Font(color="FFFFFF", size=11, bold=True), aln_c
        ws_dash[f"{cs}7"].value, ws_dash[f"{cs}7"].fill, ws_dash[f"{cs}7"].font, ws_dash[f"{cs}7"].alignment, ws_dash[f"{cs}7"].border = fk, f_white, Font(color=hx, size=18, bold=True), aln_c, brd

    for r_idx in range(9, 27):
        ws_dash.row_dimensions[r_idx].height = 20
    chart_img = f"/tmp/dash_chart_{uuid.uuid4().hex[:6]}.png"
    try:
        if chart_labels:
            fig, ax = plt.subplots(figsize=(9, 3.6), dpi=130)
            x_pos = range(len(chart_labels))
            ax.bar([i - 0.18 for i in x_pos], chart_act, width=0.35, label=_ar("المحقق الفعلي"), color="#1E3A8A")
            ax.bar([i + 0.18 for i in x_pos], chart_tgt, width=0.35, label=_ar("المستهدف"), color="#F59E0B")
            ax.set_xticks(list(x_pos))
            ax.set_xticklabels(chart_labels)
            ax.legend()
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            plt.tight_layout()
            plt.savefig(chart_img)
            plt.close(fig)
            plt.close("all")
        if os.path.exists(chart_img):
            img_xl = XLImage(chart_img)
            img_xl.width, img_xl.height = 820, 330
            ws_dash.add_image(img_xl, "B9")
    except Exception as exc:
        print("Chart Img Err:", exc, flush=True)

    ws_dash.merge_cells("B27:M27")
    ws_dash["B27"] = "💡 القراءة التحليلية والتوصيات التنفيذية"
    ws_dash["B27"].fill, ws_dash["B27"].font, ws_dash["B27"].alignment = f_navy, Font(color="FFD166", size=12, bold=True), aln_r
    ws_dash.row_dimensions[28].height = 28
    ws_dash.merge_cells("B28:M33")
    ws_dash["B28"] = summary.replace("**", "").replace("###", "").replace("##", "").strip()
    ws_dash["B28"].fill, ws_dash["B28"].font, ws_dash["B28"].border = f_white, Font(color="1E293B", size=11), brd
    ws_dash["B28"].alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)

    safe_fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "Dashboard"
    path = f"/tmp/{safe_fname}_{uuid.uuid4().hex[:6]}.xlsx"
    wb.save(path)
    send_file(cid, path, f"{safe_fname}.xlsx", MIME["xlsx"], f"📊 تم إعداد لوحة القيادة: *{title}*\n✨ تشمل: بطاقات المؤشرات التفاعلية + سجل البيانات وخطة التطوير.")
    BUS.publish("office.excel_exported", {"cid": cid, "title": title})
    if os.path.exists(chart_img):
        send_file(cid, chart_img, "Performance_Chart.png", "image/png", f"📈 الرسم البياني لمؤشرات: *{title}*")
    _drop(path, chart_img)
    del wb
    gc.collect()


def make_pptx(cid: str, msg: str) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    font_name = _detect_font(msg)
    send_msg(cid, "📊 جاري تصميم العرض التقديمي وتنسيق الشرائح والصور...")
    title = _clean_title(msg)
    prompt = f"أنشئ محتوى عرض تقديمي احترافي حول: {msg}\n" + 'JSON فقط: {"subtitle": "وصف مختصر", "slides": [{"heading": "عنوان", "points": ["نقطة 1", "نقطة 2", "نقطة 3", "نقطة 4"]}]} (6 شرائح بالعربية الفصحى).'
    data = ai_ask_json(prompt, "مصمم عروض تنفيذية.", mode="arabic") or {
        "subtitle": "عرض تحليلي واستراتيجي شامل",
        "slides": [{"heading": "نظرة عامة", "points": ["تحديد الأهداف الاستراتيجية", "تحليل الوضع الراهن", "رفع كفاءة الأداء"]}],
    }

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    NAVY, SLATE, GOLD, WHITE, LIGHT, DARK = (
        RGBColor(11, 25, 44),
        RGBColor(30, 62, 98),
        RGBColor(255, 209, 102),
        RGBColor(255, 255, 255),
        RGBColor(248, 250, 252),
        RGBColor(15, 23, 42),
    )

    def _p(tf, txt, sz, clr, bold=False, align=PP_ALIGN.RIGHT, sp=0, first=False):
        p = next(iter(tf.paragraphs)) if first else tf.add_paragraph()
        p.text, p.alignment, p.font.name, p.font.size, p.font.bold, p.font.color.rgb = txt, align, font_name, Pt(sz), bold, clr
        if sp:
            p.space_before = Pt(sp)

    s0 = prs.slides.add_slide(blank)
    s0.background.fill.solid()
    s0.background.fill.fore_color.rgb = NAVY
    bar = s0.shapes.add_shape(1, 0, Inches(6.8), Inches(13.333), Inches(0.2))
    bar.fill.solid()
    bar.fill.fore_color.rgb = GOLD
    bar.line.fill.background()
    tf0 = s0.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(2)).text_frame
    tf0.word_wrap = True
    _p(tf0, title, 40, GOLD, True, first=True)
    _p(tf0, data.get("subtitle", ""), 20, WHITE, sp=14)
    _p(tf0, f"تاريخ الإصدار: {today_dates()}", 14, RGBColor(148, 163, 184), sp=28)

    slide_img = _fetch_visual(title, f"/tmp/ppt_cover_{uuid.uuid4().hex[:6]}.jpg")
    if slide_img:
        try:
            s0.shapes.add_picture(slide_img, Inches(0.8), Inches(4.5), width=Inches(3.2))
        except Exception:
            pass
    for idx, sl in enumerate(data.get("slides", [])[:8], 1):
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = LIGHT
        for y_pos, h_sz, clr in ((0, 1.2, NAVY), (1.2, 0.08, GOLD)):
            sh = s.shapes.add_shape(1, 0, Inches(y_pos), Inches(13.333), Inches(h_sz))
            sh.fill.solid()
            sh.fill.fore_color.rgb = clr
            sh.line.fill.background()
        htf = s.shapes.add_textbox(Inches(0.8), Inches(0.25), Inches(11.7), Inches(0.7)).text_frame
        _p(htf, f"{idx}. {sl.get('heading', '')}", 26, GOLD, True, first=True)
        btf = s.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.8)).text_frame
        btf.word_wrap = True
        for pi, pt in enumerate(sl.get("points", [])):
            _p(btf, f"▪ {pt}", 20, DARK, first=(pi == 0))
            btf.paragraphs[pi].space_after = Pt(16)
        ftf = s.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.4)).text_frame
        _p(ftf, f"{title}  |  شريحة {idx}", 11, SLATE, align=PP_ALIGN.LEFT, first=True)

    fname = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_") or "Presentation"
    path = f"/tmp/{fname}_{uuid.uuid4().hex[:6]}.pptx"
    prs.save(path)
    send_file(cid, path, f"{fname}.pptx", MIME["pptx"], f"📽️ تم تصميم العرض التقديمي: *{title}*")
    BUS.publish("office.pptx_exported", {"cid": cid, "title": title})
    _drop(path, slide_img)
    del prs
    gc.collect()


def make_live_powerbi(cid: str, msg: str) -> None:
    import json

    send_msg(cid, "📊 جاري بناء لوحة القيادة التفاعلية الحية وتجهيز رابط التعديل المباشر...")
    title = _clean_title(msg)
    prompt = f"أنشئ بيانات لوحة قيادة احترافية حول: {msg}\n" + 'JSON فقط: {"title": "عنوان اللوحة", "cols": ["البند", "القسم", "المحقق", "المستهدف", "الحالة"], "rows": [["بند 1", "قسم 1", "95", "100", "ممتاز"]]}'
    board = ai_ask_json(prompt, "محلل بيانات محترف. أنشئ 6 صفوف بيانات واقعية.", mode="fast")
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
    rec = next(iter(saved), {}) if isinstance(saved, list) else (saved or {})
    bid = rec.get("id", 1) if isinstance(rec, dict) else 1
    link = f"{RENDER_URL}/board/{bid}" if RENDER_URL else f"/board/{bid}"
    send_msg(cid, f"📊 *تم إطلاق لوحة القيادة الحية بنجاح:*\n*{board.get('title', title)}*\n\n🔗 *رابط اللوحة التفاعلية للتعديل المباشر:*\n{link}")
    BUS.publish("office.live_board_created", {"cid": cid, "board_id": bid})


def make_powerbi_kit(cid: str, msg: str) -> None:
    send_msg(cid, "📈 جاري إعداد نموذج البيانات ومعادلات DAX الاحترافية...")
    title = _clean_title(msg)
    guide = ai_ask(msg, f"أنت خبير Power BI. للمشروع التالي: {msg}\nاكتب: 1. هيكل الجداول (Fact & Dimension). 2. 6 معادلات DAX جاهزة. 3. تصميم لوحة القيادة:", temperature=0.2, mode="arabic")
    _build_word_doc(cid, f"دليل هندسة Power BI: {title}", "هندسة البيانات ومعادلات DAX", [("النموذج الهندسي ومعادلات DAX", guide)], _detect_font(msg), f"📈 تم إعداد حزمة هندسة Power BI ومعادلات DAX: *{title}*", "office.powerbi_exported")

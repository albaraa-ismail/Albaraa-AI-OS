def make_excel(cid, msg):
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, PieChart, Reference

    send_msg(cid, "👥 *هندسة لوحة القيادة التفاعلية:*\n1️⃣ بناء قاعدة البيانات والمعادلات الحية...\n2️⃣ تصميم واجهة المؤشرات والرسوم البيانية...")
    print("EXCEL STEP 1: Calling AI...", flush=True)

    prompt_all = (
        "أنت مهندس بيانات خبير. أنشئ مخرجاً منظماً من 3 أقسام بالضبط مفصولة بسطر يحتوي على === فقط:\n"
        "القسم 1: عنوان رسمي ومؤسسي فخم للتقرير من 3 إلى 6 كلمات بدون أي أفعال أمر مثل (عطني، صمم، اكتب).\n"
        "القسم 2: جدول بيانات من 13 صفاً (صف عناوين + 12 صف بيانات واقعية) بـ 5 أعمدة مفصولة بعلامة | فقط:\n"
        "العمود 1: الاسم أو البند | العمود 2: الإدارة | العمود 3: المحقق الفعلي (رقم من 70 إلى 115) | العمود 4: المستهدف (رقم من 85 إلى 105) | العمود 5: ملاحظة موجزة\n"
        "القسم 3: ملخص تنفيذي من 3 نقاط قصيرة ومباشرة يبرز أهم الاستنتاجات والتوصيات.\n"
        "التزم بالفصل بعلامة === بين الأقسام الثلاثة بدون أي مقدمات."
    )
    full_res = ai_ask(msg, prompt_all)
    print("EXCEL STEP 2: AI Done, len=", len(full_res), flush=True)

    parts = [p.strip() for p in full_res.split("===") if p.strip()]
    it_parts = iter(parts)
    p1 = next(it_parts, "")
    p2 = next(it_parts, "")
    p3 = next(it_parts, "")

    formal_title = p1.replace('"', '').strip()[:60] if (p1 and len(p1) < 90 and "|" not in p1) else "تقرير مؤشرات الأداء الاستراتيجية"
    raw = p2 if "|" in p2 else full_res
    summary_txt = p3 if p3 else "تحليل مؤشرات الأداء يظهر استقراراً عاماً مع فرص لتعزيز الكفاءة التشغيلية وتحقيق المستهدفات المخططة."

    wb = openpyxl.Workbook()
    ws_dash = wb.active
    ws_dash.title = "لوحة القيادة"
    ws_dash.sheet_view.rightToLeft = True
    ws_dash.sheet_view.showGridLines = False

    ws_data = wb.create_sheet(title="البيانات والتحليل")
    ws_data.sheet_view.rightToLeft = True
    ws_data.sheet_view.showGridLines = True

    c_navy, c_slate, c_gold, c_bg, c_white = "0B192C", "1E3E62", "FFD166", "F1F5F9", "FFFFFF"
    c_card_1, c_card_2, c_card_3, c_card_4 = "1E3A8A", "0F766E", "B45309", "4338CA"

    fill_navy = PatternFill(start_color=c_navy, end_color=c_navy, fill_type="solid")
    fill_slate = PatternFill(start_color=c_slate, end_color=c_slate, fill_type="solid")
    fill_bg = PatternFill(start_color=c_bg, end_color=c_bg, fill_type="solid")
    fill_white = PatternFill(start_color=c_white, end_color=c_white, fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_green = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    fill_blue = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    fill_amber = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    thin = Side(style='thin', color='CBD5E1')
    b_cell = Border(left=thin, right=thin, top=thin, bottom=thin)

    parsed = []
    for l in raw.split("\n"):
        if "|" in l and not set(l.replace("|", "").strip()).issubset({"-", ":", " "}):
            row_vals = []
            for x in l.split("|"):
                v = x.strip().replace("**", "")
                if v and len(row_vals) < 5:
                    try: v = float(v) if "." in v else int(v)
                    except ValueError: pass
                    row_vals.append(v)
            if len(row_vals) >= 4:
                parsed.append(row_vals)

    if len(parsed) < 2:
        parsed = [
            ["البند", "القسم", "المحقق", "المستهدف", "ملاحظة"],
            ["مؤشر الكفاءة التشغيلية", "العمليات", 94, 90, "تجاوز المستهدف بنجاح"],
            ["مؤشر جودة المخرجات", "الجودة", 88, 92, "أداء مستقر ومتصاعد"],
            ["مؤشر سرعة الإنجاز", "التطوير", 96, 85, "أعلى معدل أداء"]
        ]

    headers = ["البند / الموظف", "الإدارة / التصنيف", "المحقق الفعلي", "المستهدف المخطط", "نسبة الإنجاز %", "الفارق عن المستهدف", "التقييم الآلي", "ملاحظات المتابعة"]
    ws_data.row_dimensions.height = 30
    for col_idx, h_text in enumerate(headers, start=1):
        cell = ws_data.cell(row=1, column=col_idx, value=h_text)
        cell.fill = fill_navy
        cell.font = Font(color=c_gold, bold=True, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = b_cell

    it_parsed = iter(parsed)
    next(it_parsed, None)
    data_rows = list(it_parsed)
    last_row = len(data_rows) + 1

    for idx, r in enumerate(data_rows, start=2):
        ws_data.row_dimensions[idx].height = 24
        it_r = iter(r)
        name_v = str(next(it_r, "بند تنفيذي"))
        dept_v = str(next(it_r, "عام"))
        raw_act = next(it_r, 85)
        raw_tgt = next(it_r, 90)
        note_v = str(next(it_r, "متابعة دورية مستمرة"))

        act_v = raw_act if isinstance(raw_act, (int, float)) else 85
        tgt_v = raw_tgt if isinstance(raw_tgt, (int, float)) else 90
        pct_num = round((act_v / max(tgt_v, 1)) * 100, 1)

        row_entries = [
            name_v,
            dept_v,
            act_v,
            tgt_v,
            f"=ROUND((C{idx}/MAX(D{idx},1))*100, 1)",
            f"=C{idx}-D{idx}",
            f'=IF(E{idx}>=100,"متفوق 🌟",IF(E{idx}>=85,"جيد جداً ✅","يحتاج دعم ⚠️"))',
            note_v
        ]

        for c_idx, val in enumerate(row_entries, start=1):
            cell = ws_data.cell(row=idx, column=c_idx, value=val)
            cell.border = b_cell
            cell.font = Font(color="0F172A", size=11, bold=(c_idx in (1, 5, 7)))
            cell.alignment = Alignment(horizontal="center" if c_idx in (3, 4, 5, 6, 7) else "right", vertical="center")
            if idx % 2 == 0: cell.fill = fill_zebra
            if c_idx == 7:
                if pct_num >= 100: cell.fill = fill_green
                elif pct_num >= 85: cell.fill = fill_blue
                else: cell.fill = fill_amber

    tot_row = last_row + 1
    ws_data.row_dimensions[tot_row].height = 28
    tot_entries = [
        "الإجمالي / المتوسط العام",
        f'=COUNTA(A2:A{last_row}) & " سجل"',
        f"=SUM(C2:C{last_row})",
        f"=SUM(D2:D{last_row})",
        f"=ROUND(AVERAGE(E2:E{last_row}), 1)",
        f"=SUM(F2:F{last_row})",
        f'=COUNTIF(E2:E{last_row}, ">=85") & " محقق للمعيار"',
        "مؤشر الأداء الكلي"
    ]
    for c_idx, val in enumerate(tot_entries, start=1):
        cell = ws_data.cell(row=tot_row, column=c_idx, value=val)
        cell.fill = fill_slate
        cell.font = Font(color=c_white, bold=True, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = b_cell

    for c_idx in range(1, 9):
        col_ltr = get_column_letter(c_idx)
        ws_data.column_dimensions[col_ltr].width = 24 if c_idx in (1, 8) else 18

    for r in range(1, 36):
        ws_dash.row_dimensions[r].height = 22
        for c in range(1, 14):
            ws_dash.cell(row=r, column=c).fill = fill_bg

    for c in range(1, 14):
        ws_dash.column_dimensions[get_column_letter(c)].width = 13

    ws_dash.merge_cells("B2:M3")
    ws_dash["B2"] = f"لوحة القيادة التنفيذية: {formal_title}"
    ws_dash["B2"].font = Font(color=c_gold, bold=True, size=18)
    ws_dash["B2"].fill = fill_navy
    ws_dash["B2"].alignment = Alignment(horizontal="center", vertical="center")

    ws_dash.merge_cells("B4:M4")
    ws_dash["B4"] = f"تاريخ التحديث: {today_dates()}   |   لوحة مؤشرات تفاعلية مرتبطة بالبيانات الحية"
    ws_dash["B4"].font = Font(color=c_white, size=11)
    ws_dash["B4"].fill = fill_slate
    ws_dash["B4"].alignment = Alignment(horizontal="center", vertical="center")

    cards_spec = [
        ("B", "D", "إجمالي المحقق الفعلي", f"='البيانات والتحليل'!C{tot_row}", c_card_1),
        ("E", "G", "متوسط نسبة الإنجاز %", f"='البيانات والتحليل'!E{tot_row}", c_card_2),
        ("H", "J", "صافي الفارق عن المستهدف", f"='البيانات والتحليل'!F{tot_row}", c_card_3),
        ("K", "M", "أعلى قيمة مسجلة", f"=MAX('البيانات والتحليل'!C2:C{last_row})", c_card_4),
    ]

    ws_dash.row_dimensions.height = 24
    ws_dash.row_dimensions.height = 38
    for c_start, c_end, title_k, formula_k, hex_c in cards_spec:
        ws_dash.merge_cells(f"{c_start}6:{c_end}6")
        ws_dash.merge_cells(f"{c_start}7:{c_end}7")

        top_c = ws_dash[f"{c_start}6"]
        top_c.value = title_k
        top_c.fill = PatternFill(start_color=hex_c, end_color=hex_c, fill_type="solid")
        top_c.font = Font(color=c_white, bold=True, size=11)
        top_c.alignment = Alignment(horizontal="center", vertical="center")

        val_c = ws_dash[f"{c_start}7"]
        val_c.value = formula_k
        val_c.fill = fill_white
        val_c.font = Font(color=hex_c, bold=True, size=18)
        val_c.alignment = Alignment(horizontal="center", vertical="center")

    bar_chart = BarChart()
    bar_chart.type = "col"
    bar_chart.style = 10
    bar_chart.title = "مقارنة الأداء المحقق مقابل المستهدف"
    bar_chart.y_axis.title = "القيمة"
    bar_chart.width = 21
    bar_chart.height = 11.5
    data_ref = Reference(ws_data, min_col=3, max_col=4, min_row=1, max_row=last_row)
    cats_ref = Reference(ws_data, min_col=1, min_row=2, max_row=last_row)
    bar_chart.add_data(data_ref, titles_from_data=True)
    bar_chart.set_categories(cats_ref)
    ws_dash.add_chart(bar_chart, "B9")

    pie_chart = PieChart()
    pie_chart.title = "توزيع الحصص والأوزان النسبية"
    pie_chart.style = 10
    pie_chart.width = 14.5
    pie_chart.height = 11.5
    pie_data = Reference(ws_data, min_col=3, min_row=1, max_row=min(last_row, 9))
    pie_cats = Reference(ws_data, min_col=1, min_row=2, max_row=min(last_row, 9))
    pie_chart.add_data(pie_data, titles_from_data=True)
    pie_chart.set_categories(pie_cats)
    ws_dash.add_chart(pie_chart, "I9")

    ws_dash.merge_cells("B27:M27")

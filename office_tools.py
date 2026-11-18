def edit_uploaded_excel(cid: str, file_path: str, orig_name: str, msg: str):
    """تعديل ملف إكسل مرفوع فعليًا دون حذف أو اختصار أي صف أو عمود"""
    send_msg(cid, "⏳ جاري قراءة ملف الإكسل وتطبيق التعديلات بدقة على كافة السجلات...")
    wb = openpyxl.load_workbook(file_path)
    
    # استخراج هيكل الأوراق والأعمدة وعينة من البيانات للذكاء الاصطناعي
    schema_info = []
    for sname in wb.sheetnames:
        ws = wb[sname]
        headers = [str(ws.cell(row=1, column=c).value or f"عمود_{c}") for c in range(1, ws.max_column + 1)]
        sample = [str(ws.cell(row=2, column=c).value or "") for c in range(1, ws.max_column + 1)] if ws.max_row >= 2 else []
        schema_info.append(f"ورقة '{sname}' (عدد الصفوف: {ws.max_row}): الأعمدة={headers} | مثال صف 2={sample}")

    sys_prompt = (
        "أنت مهندس بيانات Excel. لديك هيكل ملف إكسل حقيقي وتريد تنفيذ تعديلات المستخدم عليه.\n"
        "أرجع JSON فقط يحدد التعديلات المطلوبة بدقة بهذا الشكل:\n"
        '{"operations": [{"sheet": "اسم الورقة", "col_index": 4, "new_header": null, "set_all_rows_value": "ذكاء اصطناعي", "row_updates": {"2": "قيمة خاصة"}}]}\n'
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
                    # تعديل الصفوف التي تحتوي على بيانات فقط
                    if any(ws.cell(row=r, column=c).value is not None for c in range(1, ws.max_column + 1)):
                        ws.cell(row=r, column=col_idx).value = val
            for r_str, r_val in (op.get("row_updates") or {}).items():
                ws.cell(row=int(r_str), column=col_idx).value = r_val

    out_name = f"Modified_{orig_name}" if not orig_name.startswith("Modified_") else orig_name
    if not out_name.endswith(".xlsx"):
        out_name += ".xlsx"
    out_path = f"/tmp/{out_name}"
    wb.save(out_path)
    send_file(cid, out_path, out_name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"✅ تم تعديل الملف بالكامل مع الحفاظ على جميع الصفوف ({ws.max_row - 1} سجل)")

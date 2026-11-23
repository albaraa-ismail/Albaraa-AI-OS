import io
from core.config import GROQ_KEYS, URLS, rotated_keys
from core.core_ai import SESSION, ai_ask, ai_vision
from security.safe_guard import mask_saudi_pii


def transcribe_voice_note(file_url: str) -> str:
    if not file_url or not GROQ_KEYS:
        return ""
    try:
        audio_res = SESSION.get(file_url, timeout=25)
        if audio_res.status_code != 200:
            return ""
        raw_audio = audio_res.content
        for key in rotated_keys(GROQ_KEYS):
            try:
                res = SESSION.post(
                    URLS["groq_audio"],
                    headers={"Authorization": f"Bearer {key}"},
                    files={"file": ("voice.ogg", raw_audio, "audio/ogg")},
                    data={"model": "whisper-large-v3-turbo", "language": "ar"},
                    timeout=30,
                )
                if res.status_code == 200:
                    return res.json().get("text", "").strip()
            except Exception:
                continue
    except Exception as exc:
        print(f"Voice Transcribe Err: {exc}", flush=True)
    return ""


def _extract_pdf_text(raw_bytes: bytes) -> str:
    try:
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for idx, page in enumerate(pdf.pages[:15], 1):
                txt = (page.extract_text() or "").strip()
                tbl_lines = [
                    " | ".join(str(cell or "").strip() for cell in row)
                    for tbl in (page.extract_tables() or [])
                    for row in tbl
                ]
                tbl_str = "\n".join(tbl_lines).strip()
                if txt or tbl_str:
                    parts.append(f"--- صفحة {idx} ---\n{txt}\n{tbl_str}".strip())
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _extract_office_text(raw_bytes: bytes, mime_type: str) -> str:
    try:
        if any(k in mime_type for k in ("spreadsheet", "excel")):
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
            out: list[str] = []
            for sheet in wb.sheetnames[:4]:
                out.append(f"=== ورقة: {sheet} ===")
                for row in list(wb[sheet].iter_rows(values_only=True))[:60]:
                    if any(row):
                        out.append(" | ".join(str(v if v is not None else "") for v in row))
            return "\n".join(out).strip()

        if any(k in mime_type for k in ("wordprocessing", "docx")):
            from docx import Document

            doc = Document(io.BytesIO(raw_bytes))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()][:80]
            for tbl in doc.tables[:5]:
                for row in tbl.rows:
                    paras.append(" | ".join(c.text.strip() for c in row.cells))
            return "\n".join(paras).strip()

        if any(k in mime_type for k in ("presentation", "pptx")):
            from pptx import Presentation

            prs = Presentation(io.BytesIO(raw_bytes))
            slides_txt: list[str] = []
            for idx, slide in enumerate(prs.slides[:20], 1):
                lines = [sh.text.strip() for sh in slide.shapes if getattr(sh, "has_text_frame", False) and sh.text.strip()]
                if lines:
                    slides_txt.append(f"--- شريحة {idx} ---\n" + "\n".join(lines))
            return "\n".join(slides_txt).strip()
    except Exception:
        pass
    return ""


def _summarize_extracted(raw_text: str, user_prompt: str, default_q: str, sys_role: str, limit: int = 8500) -> str:
    safe_txt = mask_saudi_pii(raw_text[:limit])
    return ai_ask(f"{user_prompt or default_q}\n\nالمحتوى:\n{safe_txt}", sys_role, mode="arabic")


def read_media_from_url(file_url: str, mime_type: str = "image/jpeg", user_prompt: str = "") -> str:
    if mime_type.startswith("audio/"):
        transcript = transcribe_voice_note(file_url)
        return f"🎙 *نص البصمة الصوتية:*\n{transcript}" if transcript else "⚠️ تعذر تفريغ البصمة الصوتية."

    if not file_url:
        return "⚠️ تعذر الوصول لرابط الملف."

    try:
        res = SESSION.get(file_url, timeout=30)
        if res.status_code != 200:
            return "⚠️ تعذر تحميل الملف من الرابط."
        raw_bytes = res.content

        if any(k in mime_type for k in ("spreadsheet", "excel", "wordprocessing", "docx", "presentation", "pptx")):
            if extracted := _extract_office_text(raw_bytes, mime_type):
                return _summarize_extracted(
                    extracted,
                    user_prompt,
                    "حلل هذه البيانات واستخرج أهم المؤشرات والنتائج والملخص التنفيذي باللغة العربية:",
                    "أنت محلل بيانات ومستندات محترف.",
                )

        if "pdf" in mime_type:
            if len(pdf_txt := _extract_pdf_text(raw_bytes)) > 80:
                return _summarize_extracted(
                    pdf_txt,
                    user_prompt,
                    "لخص هذا المستند واستخرج كافة الأرقام والجداول والتوصيات بدقة:",
                    "أنت باحث ومحلل مستندات محترف.",
                    limit=9000,
                )

        prompt = user_prompt or "حلل محتوى هذه الصورة أو الوثيقة بدقة واستخرج جميع النصوص والأرقام والجداول باللغة العربية بدون مقدمات."
        vision_reply = ai_vision(raw_bytes, mime_type, prompt)
        return mask_saudi_pii(vision_reply) if vision_reply else "⚠️ تعذر تحليل الصورة حالياً."
    except Exception as exc:
        print(f"Media URL Read Err: {exc}", flush=True)
        return "⚠️ تعذر تحليل الملف أو الصورة حالياً."

import os
import io
import base64
import requests
from core.core_ai import GEM_KEYS, GROQ_KEYS, GEMINI_BASE_URL, SESSION, _rotated, ai_ask
from security.safe_guard import mask_saudi_pii


def transcribe_voice_note(file_url: str) -> str:
    if not file_url or not GROQ_KEYS:
        return ""
    whisper_url = "".join(["https:/", "/api.groq.", "com/openai/v1/audio/transcriptions"])
    try:
        audio_res = SESSION.get(file_url, timeout=25)
        if audio_res.status_code != 200:
            return ""
        raw_audio = audio_res.content
        for key in _rotated(GROQ_KEYS):
            r = requests.post(
                whisper_url,
                headers={"Authorization": f"Bearer {key}"},
                files={"file": ("voice.ogg", raw_audio, "audio/ogg")},
                data={"model": "whisper-large-v3-turbo", "language": "ar"},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json().get("text", "").strip()
    except Exception as exc:
        print(f"Voice Transcribe Err: {exc}", flush=True)
    return ""
def _extract_pdf_text(raw_bytes: bytes) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for idx, page in enumerate(pdf.pages[:15], 1):
                txt = page.extract_text() or ""
                tables = page.extract_tables() or []
                tbl_str = ""
                for t in tables:
                    for row in t:
                        tbl_str += " | ".join([str(c or "").strip() for c in row]) + "\n"
                if txt.strip() or tbl_str.strip():
                    text_parts.append(f"--- صفحة {idx} ---\n{txt}\n{tbl_str}")
        return "\n".join(text_parts).strip()
    except Exception:
        return ""


def _extract_office_text(raw_bytes: bytes, mime_type: str) -> str:
    try:
        if "spreadsheet" in mime_type or "excel" in mime_type:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
            out = []
            for sheet in wb.sheetnames[:4]:
                ws = wb[sheet]
                out.append(f"=== ورقة: {sheet} ===")
                for row in list(ws.iter_rows(values_only=True))[:60]:
                    if any(row):
                        out.append(" | ".join([str(v if v is not None else "") for v in row]))
            return "\n".join(out).strip()
        if "wordprocessing" in mime_type or "docx" in mime_type:
            from docx import Document
            doc = Document(io.BytesIO(raw_bytes))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()][:80]
            for tbl in doc.tables[:5]:
                for r in tbl.rows:
                    paras.append(" | ".join([c.text.strip() for c in r.cells]))
            return "\n".join(paras).strip()
    except Exception:
        pass
    return ""


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

        # 1. معالجة ملفات Word و Excel مباشرة
        if any(k in mime_type for k in ("spreadsheet", "excel", "wordprocessing", "docx")):
            extracted = _extract_office_text(raw_bytes, mime_type)
            if extracted:
                safe_txt = mask_saudi_pii(extracted[:8000])
                q = user_prompt or "حلل هذه البيانات واستخرج أهم المؤشرات والنتائج والملخص التنفيذي باللغة العربية:"
                return ai_ask(f"{q}\n\nمحتوى الملف:\n{safe_txt}", "أنت محلل بيانات ومستندات محترف.", mode="arabic")

        # 2. معالجة ملفات PDF النصية والجداول عبر pdfplumber
        if "pdf" in mime_type:
            pdf_txt = _extract_pdf_text(raw_bytes)
            if len(pdf_txt) > 80:
                safe_txt = mask_saudi_pii(pdf_txt[:9000])
                q = user_prompt or "لخص هذا المستند واستخرج كافة الأرقام والجداول والتوصيات بدقة:"
                return ai_ask(f"{q}\n\nمحتوى PDF:\n{safe_txt}", "أنت باحث ومحلل مستندات محترف.", mode="arabic")

        # 3. الرؤية الحاسوبية للصور وملفات PDF المصورة (سكانر)
        if not GEM_KEYS:
            return "⚠️ تعذر تحليل الصورة لعدم توفر مفتاح الرؤية."
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        prompt = user_prompt or "حلل محتوى هذه الصورة أو الوثيقة بدقة واستخرج جميع النصوص والأرقام والجداول باللغة العربية بدون مقدمات."
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ]
            }]
        }
        for key in _rotated(GEM_KEYS):
            r = SESSION.post(f"{GEMINI_BASE_URL}gemini-2.0-flash:generateContent?key={key}", json=payload, timeout=35)
            if r.status_code == 200:
                ans = r.json()["candidates"]["content"]["parts"]["text"].strip()
                return mask_saudi_pii(ans)
    except Exception as exc:
        print(f"Media URL Read Err: {exc}", flush=True)
    return "⚠️ تعذر تحليل الملف أو الصورة حالياً."

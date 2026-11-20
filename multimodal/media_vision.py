import os
import base64
from core.core_ai import GEM_KEYS, GEMINI_BASE_URL, SESSION


def extract_document_text(path: str) -> str:
    """استخراج النصوص من ملفات PDF و Word و Excel بدقة عالية."""
    if not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages[:15]).strip()
        if ext in (".docx", ".doc"):
            from docx import Document
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
        if ext in (".xlsx", ".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            lines = []
            for ws in wb.worksheets[:3]:
                for row in ws.iter_rows(max_row=60, values_only=True):
                    vals = [str(c) for c in row if c is not None]
                    if vals:
                        lines.append(" | ".join(vals))
            return "\n".join(lines).strip()
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(12000)
    except Exception as exc:
        print(f"Doc Extract Err: {exc}", flush=True)
        return ""


def analyze_multimodal_file(path: str, mime_type: str = "image/jpeg", prompt: str = "") -> str:
    """قراءة وتحليل الصور والوثائق عبر نماذج الرؤية الحاسوبية."""
    if not os.path.exists(path):
        return "⚠ الملف غير موجود على الخادم."

    if any(path.lower().endswith(e) for e in (".pdf", ".docx", ".xlsx", ".txt", ".csv")):
        text_content = extract_document_text(path)
        if text_content:
            return f"📄 *المحتوى المستخرج من الوثيقة:*\n{text_content[:4000]}"

    if not GEM_KEYS:
        return "⚠ مفاتيح محرك الرؤية غير مفعلة."

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    ask_txt = prompt or "حلل هذه الصورة أو الوثيقة بدقة واستخرج كافة البيانات والنصوص والأرقام باللغة العربية."
    payload = {
        "contents": [{
            "parts": [
                {"text": ask_txt},
                {"inline_data": {"mime_type": mime_type, "data": b64}},
            ]
        }]
    }
    for key in GEM_KEYS:
        try:
            r = SESSION.post(f"{GEMINI_BASE_URL}gemini-2.0-flash:generateContent?key={key}", json=payload, timeout=35)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            continue
    return "⚠ تعذر تحليل الصورة حالياً."

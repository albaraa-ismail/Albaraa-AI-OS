import os
import re
import base64
import logging
import requests
import openpyxl
from docx import Document
from pypdf import PdfReader
from bs4 import BeautifulSoup
from core_ai import GEM_KEY, GROQ_KEY, GEMINI_BASE_URL, SESSION

logger = logging.getLogger("MediaVision")

# خزينة لحفظ آخر ملف أو وسائط أرسلها المستخدم في كل محادثة
MEDIA_VAULT = {}

def download_whatsapp_file(url: str, filename: str) -> str:
    """تحميل الملفات أو الصور أو الفيديوهات من رابط Green-API"""
    try:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename) or "file.bin"
        local_path = f"/tmp/{int(os.times().elapsed * 100)}_{safe_name}"
        res = SESSION.get(url, timeout=30)
        if res.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(res.content)
            return local_path
    except Exception as e:
        logger.error(f"Download error: {e}")
    return ""

def scrape_url(url: str) -> str:
    """قراءة واستخراج محتوى أي رابط موقع إلكتروني"""
    try:
        res = SESSION.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = "\n".join([line.strip() for line in soup.get_text().splitlines() if line.strip()])
            return text[:12000]
    except Exception as e:
        logger.warning(f"Scrape error for {url}: {e}")
    return ""

def extract_document_text(path: str) -> str:
    """قراءة محتوى أي ملف (Excel, Word, PDF, CSV, Code) بالكامل"""
    ext = os.path.splitext(path).lower()
    try:
        if ext in (".xlsx", ".xlsm"):
            wb = openpyxl.load_workbook(path, data_only=True)
            out = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                out.append(f"--- ورقة: {sheet} (عدد الصفوف: {ws.max_row}) ---")
                for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                    if any(row):
                        out.append(f"صف {r_idx}: " + " | ".join([str(c if c is not None else "") for c in row]))
            return "\n".join(out)[:15000]

        elif ext == ".docx":
            doc = Document(path)
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for t in doc.tables:
                for row in t.rows:
                    parts.append(" | ".join([c.text.strip() for c in row.cells]))
            return "\n".join(parts)[:15000]

        elif ext == ".pdf":
            reader = PdfReader(path)
            pages = [f"--- صفحة {i+1} ---\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages)]
            return "\n".join(pages)[:15000]

        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:15000]
    except Exception as e:
        logger.error(f"Document read error: {e}")
        return ""

def analyze_multimodal_file(path: str, mime_type: str, user_prompt: str) -> str:
    """تحليل الصور والفيديوهات والصوتيات عبر الذكاء الاصطناعي البصري"""
    if not GEM_KEY or not os.path.exists(path):
        return "⚠️ تحليل الصور والفيديو يتطلب تفعيل مفتاح Gemini API."

    try:
        with open(path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        list_url = f"{GEMINI_BASE_URL.rstrip('/')}?key={GEM_KEY}"
        g_res = SESSION.get(list_url, timeout=8)
        g_models = ["gemini-1.5-flash"]
        if g_res.status_code == 200:
            found = [
                m["name"].replace("models/", "")
                for m in g_res.json().get("models", [])
                if "flash" in m["name"].lower() and "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            if found:
                g_models = found

        prompt = user_prompt or "حلل هذا المحتوى بدقة واحترافية باللغة العربية واستخرج جميع التفاصيل والنصوص المهمة منه."
        for model in g_models[:2]:
            url = f"{GEMINI_BASE_URL}{model}:generateContent?key={GEM_KEY}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": b64_data}}
                    ]
                }]
            }
            res = SESSION.post(url, json=payload, timeout=45)
            if res.status_code == 200:
                return res.json()["candidates"]["content"]["parts"]["text"].strip()
    except Exception as e:
        logger.error(f"Multimodal analysis error: {e}")
    return "⚠️ تعذر تحليل الوسائط حاليًا، تأكد من حجم الملف أو صيغته."

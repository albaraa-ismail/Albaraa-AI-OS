import os
import json
import base64
import requests

# إعداد جلسة اتصال موحدة وسريعة لجميع الملفات
SESSION = requests.Session()

# مفاتيح الاتصال المربوطة في Render
SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
G_URL = os.environ.get("GREEN_API_URL", "https://green-api.com").strip().rstrip("/")

GEMINI_BASE_URL = "https://googleapis.com"

# قاعدة الحوكمة الجديدة: منع تأليف الأرقام الوهمية والالتزام بالحقائق
STRICT_POLICY = (
    "\n[قواعد الحوكمة والدقة الصارمة]: "
    "1. التزم باللغة العربية الفصحى الواضحة والمهنية. "
    "2. ممنوع منعاً باتاً اختراع أو تأليف أي أرقام أو إحصائيات أو ميزانيات غير موجودة في البيانات المرفقة أو نتائج البحث. "
    "3. إذا لم تتوفر أرقام حقيقية، استخدم التقديرات المنطقية الواضحة أو اذكر أن البيانات قيد القياس."
)

def sb(method: str, table: str, data=None, q: str = ""):
    """التواصل المباشر مع قاعدة بيانات Supabase"""
    if not SB_URL or not SB_KEY:
        return []
    url = f"{SB_URL.rstrip('/')}/rest/v1/{table}{q}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        r = SESSION.request(method, url, headers=headers, json=data, timeout=15)
        if r.status_code in (200, 201):
            return r.json()
    except Exception as e:
        print(f"Supabase Err ({table}): {e}", flush=True)
    return []

def ai_ask(prompt: str, system_prompt: str = "", temperature: float = 0.3) -> str:
    """محرك الذكاء الاصطناعي متعدد النماذج مع التبديل التلقائي لمنع التوقف"""
    full_sys = (system_prompt + STRICT_POLICY).strip()

    # 1. المحاولة الأولى: Gemini (الأقوى في التحليل واللغة العربية)
    if GEM_KEY:
        for model in ("gemini-2.5-flash", "gemini-2.0-flash"):
            try:
                url = f"{GEMINI_BASE_URL}{model}:generateContent?key={GEM_KEY}"
                payload = {
                    "systemInstruction": {"parts": [{"text": full_sys}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temperature}
                }
                r = SESSION.post(url, json=payload, timeout=45)
                if r.status_code == 200:
                    data = r.json()
                    txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if txt:
                        return txt
            except Exception as e:
                print(f"Gemini ({model}) Err: {e}", flush=True)

    # 2. المحاولة الثانية: OpenRouter (بديل سحابي موثوق)
    if OR_KEY:
        try:
            url = "https://openrouter.ai"
            headers = {
                "Authorization": f"Bearer {OR_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "google/gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": full_sys},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature
            }
            r = SESSION.post(url, headers=headers, json=payload, timeout=45)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt:
                    return txt
        except Exception as e:
            print(f"OpenRouter Err: {e}", flush=True)

    # 3. المحاولة الثالثة: Groq (الأسرع كخط دفاع أخير)
    if GROQ_KEY:
        try:
            url = "https://groq.com"
            headers = {
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": full_sys},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature
            }
            r = SESSION.post(url, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt:
                    return txt
        except Exception as e:
            print(f"Groq Err: {e}", flush=True)

    return "⚠ تعذر الحصول على استجابة من محركات الذكاء الاصطناعي حالياً، يرجى المحاولة بعد قليل."

def send_msg(cid: str, text: str):
    """إرسال رسالة نصية عبر Green-API للواتساب"""
    if not G_ID or not G_TOK or not cid:
        return
    url = f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}"
    try:
        SESSION.post(url, json={"chatId": cid, "message": text}, timeout=20)
    except Exception as e:
        print(f"SendMsg Err: {e}", flush=True)

def send_file(cid: str, file_path: str, filename: str, mime_type: str = "", caption: str = ""):
    """إرسال ملف (Word, Excel, PPTX, Video, Image) عبر Green-API للواتساب"""
    if not G_ID or not G_TOK or not cid or not os.path.exists(file_path):
        return
    url = f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type or "application/octet-stream")}
            data = {"chatId": cid, "fileName": filename, "caption": caption}
            SESSION.post(url, data=data, files=files, timeout=60)
    except Exception as e:
        print(f"SendFile Err: {e}", flush=True)

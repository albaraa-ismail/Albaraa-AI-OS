import os, requests, base64, json, time, threading, openpyxl
from pptx import Presentation
from pptx.util import Pt
from docx import Document
from duckduckgo_search import DDGS
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)
ai_os = MultiAgentSystem()
PROCESSED_IDS = set()

G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()

def dec(s):
    return base64.b64decode(s).decode("utf-8")

def sb_req(method, table, payload=None, query=""):
    if not SB_URL or not SB_KEY:
        return list()
    url = f"{SB_URL}/rest/v1/{table}{query}"
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    try:
        r = requests.get(url, headers=h, timeout=10) if method == "GET" else requests.post(url, json=payload, headers=h, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
    except Exception:
        pass
    return list()

def live_search(query):
    try:
        results = list()
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(f"- {r.get('title', '')}: {r.get('body', '')}")
        return "\n".join(results)
    except Exception:
        return ""

def call_groq(prompt, sys_role):
    url = dec("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=")
    h = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {"model": "llama-3.3-70b-versatile", "messages": ({"role": "system", "content": sys_role}, {"role": "user", "content": prompt})}
    try:
        r = requests.post(url, json=body, headers=h, timeout=30)
        if r.status_code == 200:
            return r.json().get("choices", list()).pop(0).get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return ""

def call_gemini(prompt):
    base = dec("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscw==")
    url = f"{base}/gemini-2.5-flash:generateContent?key={GEM_KEY}"
    try:
        r = requests.post(url, json={"contents": ({"parts": ({"text": prompt},)},)}, timeout=30)
        if r.status_code == 200:
            c = r.json().get("candidates", list())
            if c:
                return c.pop(0).get("content", {}).get("parts", list()).pop(0).get("text", "").strip()
    except Exception:
        pass
    return ""

def call_or(prompt, draft, lessons=""):
    url = dec("aHR0cHM6Ly9vcGVucm91dGVyLmFpL2FwaS92MS9jaGF0L2NvbXBsZXRpb25z")
    h = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
    sys_m = "أنت وكيل الحوكمة والتصحيح الذاتي في Albaraa Ai os. راجع المسودة وحسّنها مستفيداً من الدروس السابقة:\n" + lessons
    body = {"model": "openrouter/free", "messages": ({"role": "system", "content": sys_m}, {"role": "user", "content": f"الطلب: {prompt}\nالمسودة:\n{draft}"})}
    try:
        r = requests.post(url, json=body, headers=h, timeout=30)
        if r.status_code == 200:
            return r.json().get("choices", list()).pop(0).get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return draft

def send_msg(chat_id, text):
    g = dec("aHR0cHM6Ly83MTA3LmFwaS5ncmVlbmFwaS5jb20=")
    requests.post(f"{g}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": chat_id, "message": text}, timeout=15)

def send_file(chat_id, path, name, mime, cap):
    g = dec("aHR0cHM6Ly83MTA3LmFwaS5ncmVlbmFwaS5jb20=")
    with open(path, "rb") as f:
        requests.post(f"{g}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": chat_id, "caption": cap}, files={"file": (name, f, mime)}, timeout=30)

def make_excel(chat_id, prompt, custom_rows=None, title="تقرير بيانات"):
    if not custom_rows:
        sys_j = 'أعد JSON فقط: {"title": "عنوان", "rows": (("عمود1", "عمود2"), ("قيمة1", "قيمة2"))}'
        raw = call_groq(prompt, sys_j) or call_gemini(f"{sys_j}\n{prompt}")
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        rows = data.get("rows", list())
        title = data.get("title", title)
    else:
        rows = custom_rows
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.sheet_view.rightToLeft = True
    for r in rows:
        ws.append(list(r))
    wb.save("/tmp/Out.xlsx")
    send_file(chat_id, "/tmp/Out.xlsx", "Albaraa_Output.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"📊 *{title}* | Albaraa Ai os")

def make_pptx(chat_id, prompt):
    sys_j = 'أعد JSON فقط: {"main_title": "العنوان", "slides": ({"title": "شريحة", "points": ("نقطة 1", "نقطة 2")},)}'
    raw = call_groq(prompt, sys_j) or call_gemini(f"{sys_j}\n{prompt}")
    data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    prs = Presentation()
    s0 = prs.slides.add_slide(prs.slide_layouts.pop(0))
    s0.shapes.title.text = data.get("main_title", "عرض تقديمي")
    s0.placeholders.pop(1).text = "إعداد منظومة Albaraa Ai os"
    for s in data.get("slides", list()):
        sl = prs.slides.add_slide(prs.slide_layouts.pop(1))
        sl.shapes.title.text = s.get("title", "")
        tf = sl.placeholders.pop(1).text_frame
        tf.clear()
        for i, pt in enumerate(s.get("points", list())):
            p = tf.paragraphs.pop(0) if i == 0 else tf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(20)
    prs.save("/tmp/Out.pptx")
    send_file(chat_id, "/tmp/Out.pptx", "Albaraa_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ عرض تقديمي جاهز | Albaraa Ai os")

def make_docx(chat_id, prompt):
    sys_j = 'أعد JSON فقط: {"title": "عنوان التقرير", "sections": ({"heading": "عنوان فرعي", "content": "فقرة تفصيلية"},)}'
    raw = call_groq(prompt, sys_j) or call_gemini(f"{sys_j}\n{prompt}")
    data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    doc = Document()
    doc.add_heading(data.get("title", "تقرير رسمي"), 0)
    doc.add_paragraph("إعداد: منظومة Albaraa Ai os الهندسية")
    for sec in data.get("sections", list()):
        doc.add_heading(sec.get("heading", ""), level=1)
        doc.add_paragraph(sec.get("content", ""))
    doc.save("/tmp/Out.docx")
    send_file(chat_id, "/tmp/Out.docx", "Albaraa_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 مستند وورد رسمي جاهز | Albaraa Ai os")

def process_task(chat_id, user_msg, role, sender_name):
    t0 = time.time()
    low = user_msg.lower()

    if role == "admin" and user_msg.startswith(("ابن وكيل", "انشئ وكيل", "أنشئ وكيل")):
        spec = call_groq(f"صمم وكيل ذكي لـ: {user_msg}", 'أعد JSON فقط: {"unit": "الوحدة", "name": "الاسم", "subs": "3 مساعدين", "prompt": "التعليمات"}')
        try:
            ag = json.loads(spec[spec.find("{"):spec.rfind("}") + 1])
            sb_req("POST", "agents_registry", {"unit_name": ag.get("unit", "مخصصة"), "agent_name": ag.get("name", "وكيل جديد"), "sub_agents": ag.get("subs", "3 مساعدين"), "system_prompt": ag.get("prompt", user_msg)})
            send_msg(chat_id, f"🧬 *مصنع الوكلاء:* تم بناء وتفعيل الوكيل *{ag.get('name')}* في الذاكرة السحابية!")
        except Exception:
            send_msg(chat_id, "✅ تم حفظ الوكيل الجديد في الذاكرة.")
        return

    if role == "admin" and any(k in low for k in ("تقرير القياس", "جدول القياس", "احصائيات")):
        logs = sb_req("GET", "telemetry_kpis", query="?order=id.desc&limit=50")
        rows = list()
        rows.append(("العملية", "الدور", "الوحدة", "الزمن(ث)", "الوقت الموفر(د)", "مؤشر التطور", "المخرج"))
        for i in logs:
            rows.append((i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")))
        make_excel(chat_id, "", custom_rows=rows, title="جدول القياس وتطور المستخدم")
        return

    deliverable = "تقرير وبناء هندسي"
    if any(k in low for k in ("عرض", "بوربوينت", "شرائح", "pptx")):
        send_msg(chat_id, "⏳ جاري تصميم العرض التقديمي...")
        make_pptx(chat_id, user_msg)
        deliverable = "PowerPoint"
    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")):
        send_msg(chat_id, "⏳ جاري إعداد ملف الإكسل...")
        make_excel(chat_id, user_msg)
        deliverable = "Excel"
    elif any(k in low for k in ("وورد", "word", "docx", "تقرير رسمي", "خطاب")):
        send_msg(chat_id, "⏳ جاري صياغة وتنسيق مستند الوورد...")
        make_docx(chat_id, user_msg)
        deliverable = "Word"
    else:
        web_info = live_search(user_msg)
        past = sb_req("GET", "self_learning_logs", query="?order=id.desc&limit=3")
        custom_ag = sb_req("GET", "agents_registry", query="?order=id.desc&limit=12")
        lessons = "\n".join(tuple(x.get("lesson_learned", "") for x in past))
        extra_agents = "\n".join(tuple(f"{a.get('agent_name')}: {a.get('system_prompt')}" for a in custom_ag))
        sys_r = (
            "أنت منظومة Albaraa Ai os الهندسية (وحدات: علم البيانات، Python، Power BI، منصة بلدي، والمسيّرات والأنظمة الدفاعية). "
            f"الوكلاء الإضافيون المفعلون:\n{extra_agents}\n"
            "إذا طلب المستخدم بناء منصة أو نظام أو كود، صمم له الهيكل واكتب له الكود البرمجي الكامل خطوة بخطوة باللغة العربية."
        )
        full_prompt = f"الطلب: {user_msg}\n\nنتائج البحث الحي من الإنترنت:\n{web_info}" if web_info else user_msg
        draft = call_groq(full_prompt, sys_r) or call_gemini(f"{sys_r}\n{full_prompt}") or "تعذر الاتصال."
        ans = call_or(user_msg, draft, lessons) if OR_KEY else draft

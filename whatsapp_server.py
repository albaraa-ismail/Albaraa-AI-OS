import os, requests, base64, json, time, openpyxl
from pptx import Presentation
from pptx.util import Pt
from flask import Flask, request, jsonify
from main import MultiAgentSystem

app = Flask(__name__)
ai_os = MultiAgentSystem()

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
    except Exception as e:
        print("SB:", e, flush=True)
    return list()

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
    s0.placeholders.pop(1).text = "إعداد نظام Albaraa Ai os"
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

@app.route("/", methods=("GET",))
def home():
    return jsonify({"status": "online", "version": "v4.1"}), 200

@app.route("/whatsapp-webhook", methods=("POST",))
def whatsapp_webhook():
    t0 = time.time()
    data = request.get_json(silent=True) or {}
    wid = data.get('instanceData', {}).get('wid', '')
    sender_d = data.get('senderData', {})
    chat_id = sender_d.get('chatId') or data.get('chatId', '')
    sender_name = sender_d.get('senderName', 'أحمد عز الدين')
    msg_d = data.get('messageData', {})
    user_msg = (msg_d.get('textMessageData', {}).get('textMessage') or msg_d.get('extendedTextMessageData', {}).get('text') or "").strip()

    if not user_msg or user_msg.startswith(("🤖", "📊", "📽️", "⏳", "✅", "🧬")):
        return jsonify({"status": "ignored"}), 200

    is_admin = (wid and chat_id == wid)
    is_lab = ("@g.us" in chat_id)

    if user_msg == "تفعيل" and is_lab:
        sb_req("POST", "users_and_roles", {"phone_or_chat_id": chat_id, "user_name": "أحمد عز الدين", "role": "co_lead", "specialty": "Data Science & GovTech"})
        send_msg(chat_id, "✅ *تم تفعيل مختبر Albaraa Ai os بنجاح!*\nمرحباً بك يا أ. أحمد عز الدين.\nجميع وحدات (علم البيانات، Python، Power BI، Excel، منصة بلدي، وبناء الأنظمة) جاهزة لخدمتك الآن.")
        return jsonify({"status": "activated"}), 200

    if not is_admin and not is_lab:
        return jsonify({"status": "unauthorized"}), 200

    role = "admin" if is_admin else "co_lead"
    low = user_msg.lower()

    if is_admin and user_msg.startswith(("ابن وكيل", "انشئ وكيل", "أنشئ وكيل")):
        spec = call_groq(f"صمم وكيل ذكي لـ: {user_msg}", 'أعد JSON فقط: {"unit": "الوحدة", "name": "الاسم", "subs": "3 مساعدين", "prompt": "التعليمات"}')
        try:
            ag = json.loads(spec[spec.find("{"):spec.rfind("}") + 1])
            sb_req("POST", "agents_registry", {"unit_name": ag.get("unit", "مخصصة"), "agent_name": ag.get("name", "وكيل جديد"), "sub_agents": ag.get("subs", "3 مساعدين"), "system_prompt": ag.get("prompt", user_msg)})
            send_msg(chat_id, f"🧬 *مصنع الوكلاء:* تم بناء وتفعيل الوكيل *{ag.get('name')}* في الذاكرة السحابية!")
        except Exception:
            send_msg(chat_id, "✅ تم حفظ الوكيل الجديد في الذاكرة.")
        return jsonify({"status": "agent_ok"}), 200

    if is_admin and any(k in low for k in ("تقرير القياس", "جدول القياس", "احصائيات")):
        logs = sb_req("GET", "telemetry_kpis", query="?order=id.desc&limit=50")
        rows = list()
        rows.append(("العملية", "الدور", "الوحدة", "الزمن(ث)", "الوقت الموفر(د)", "مؤشر التطور", "المخرج"))
        for i in logs:
            rows.append((i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")))
        make_excel(chat_id, "", custom_rows=rows, title="جدول القياس وتطور المستخدم")
        return jsonify({"status": "kpi_ok"}), 200

    deliverable = "تقرير وبناء هندسي"
    if any(k in low for k in ("عرض", "بوربوينت", "شرائح", "pptx")):
        send_msg(chat_id, "⏳ جاري تصميم العرض التقديمي...")
        make_pptx(chat_id, user_msg)
        deliverable = "PowerPoint"
    if any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")):
        send_msg(chat_id, "⏳ جاري إعداد ملف الإكسل...")
        make_excel(chat_id, user_msg)
        deliverable = "Excel"
    if deliverable == "تقرير وبناء هندسي":
        past = sb_req("GET", "self_learning_logs", query="?order=id.desc&limit=3")
        lessons = "\n".join(tuple(x.get("lesson_learned", "") for x in past))
        sys_r = (
            "أنت منظومة Albaraa Ai os الهندسية (وحدات: علم البيانات، Python، Power BI، منصة بلدي، والمسيّرات والأنظمة الدفاعية). "
            "إذا طلب المستخدم بناء منصة أو نظام أو أتمتة، لا تكتفِ بالنصائح بل صمم له الهيكل الكامل واكتب له الكود البرمجي الجاهز للتنفيذ خطوة بخطوة باللغة العربية."
        )
        draft = call_groq(user_msg, sys_r) or call_gemini(f"{sys_r}\n{user_msg}") or "تعذر الاتصال."
        ans = call_or(user_msg, draft, lessons) if OR_KEY else draft
        sb_req("POST", "self_learning_logs", {"user_role": role, "task_type": "بناء وهندسة", "lesson_learned": f"تم بناء وتنفيذ طلب ({sender_name}): {user_msg[:50]}"})
        send_msg(chat_id, f"🤖 *Albaraa Ai os — وحدة الهندسة والبناء*\n━━━━━━━━━━━━━━━━━━\n{ans}\n━━━━━━━━━━━━━━━━━━\n🧠 *التعلم الرجعي والذاكرة:* محدثة ✅")

    elapsed = round(time.time() - t0, 2)

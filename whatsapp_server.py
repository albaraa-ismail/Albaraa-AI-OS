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

def dec(b64_str):
    return base64.b64decode(b64_str).decode("utf-8")

def sb_request(method, table, payload=None, query=""):
    if not SB_URL or not SB_KEY:
        return list()
    url = f"{SB_URL}/rest/v1/{table}{query}"
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
    except Exception as e:
        print("SB err:", e, flush=True)
    return list()

def call_groq(prompt, sys_role):
    url = dec("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=")
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": (
            {"role": "system", "content": sys_role},
            {"role": "user", "content": prompt}
        )
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=25)
        if r.status_code == 200:
            return r.json().get("choices", list()).pop(0).get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return ""

def call_gemini(prompt):
    base = dec("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscw==")
    url = f"{base}/gemini-2.5-flash:generateContent?key={GEM_KEY}"
    body = {"contents": ({"parts": ({"text": prompt},)},)}
    try:
        r = requests.post(url, json=body, timeout=25)
        if r.status_code == 200:
            c = r.json().get("candidates", list())
            if c:
                return c.pop(0).get("content", {}).get("parts", list()).pop(0).get("text", "").strip()
    except Exception:
        pass
    return ""

def call_openrouter(prompt, draft, lessons=""):
    url = dec("aHR0cHM6Ly9vcGVucm91dGVyLmFpL2FwaS92MS9jaGF0L2NvbXBsZXRpb25z")
    headers = {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"}
    sys_msg = (
        "أنت وكيل الحوكمة والتصحيح الذاتي في نظام Albaraa Ai os. "
        "راجع المسودة، صحح أي أخطاء، واستفد من الدروس السابقة التالية لتحسين الجودة:\n" + lessons
    )
    body = {
        "model": "openrouter/free",
        "messages": (
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": f"الطلب: {prompt}\nالمسودة:\n{draft}"}
        )
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=25)
        if r.status_code == 200:
            return r.json().get("choices", list()).pop(0).get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return draft

def send_msg(chat_id, text):
    g_base = dec("aHR0cHM6Ly83MTA3LmFwaS5ncmVlbmFwaS5jb20=")
    url = f"{g_base}/waInstance{G_ID}/sendMessage/{G_TOK}"
    requests.post(url, json={"chatId": chat_id, "message": text}, timeout=15)

def send_file(chat_id, path, name, mime, caption):
    g_base = dec("aHR0cHM6Ly83MTA3LmFwaS5ncmVlbmFwaS5jb20=")
    url = f"{g_base}/waInstance{G_ID}/sendFileByUpload/{G_TOK}"
    with open(path, "rb") as f:
        files = {"file": (name, f, mime)}
        requests.post(url, data={"chatId": chat_id, "caption": caption}, files=files, timeout=30)

def build_excel(chat_id, prompt, custom_rows=None, title="تقرير بيانات"):
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
    path = "/tmp/Albaraa_Output.xlsx"
    wb.save(path)
    send_file(chat_id, path, "Albaraa_Output.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"📊 *{title}* | Albaraa Ai os")

def build_pptx(chat_id, prompt):
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
    path = "/tmp/Albaraa_Presentation.pptx"
    prs.save(path)
    send_file(chat_id, path, "Albaraa_Presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ عرض تقديمي جاهز | Albaraa Ai os")

@app.route("/", methods=("GET",))
def home():
    return jsonify({"status": "online", "system": "Albaraa Ai os v4.0 Enterprise"}), 200

@app.route("/whatsapp-webhook", methods=("POST",))
def whatsapp_webhook():
    t0 = time.time()
    data = request.get_json(silent=True) or {}
    wid = data.get('instanceData', {}).get('wid', '')
    sender_data = data.get('senderData', {})
    chat_id = sender_data.get('chatId') or data.get('chatId', '')
    msg_data = data.get('messageData', {})
    user_msg = (msg_data.get('textMessageData', {}).get('textMessage') or 
                msg_data.get('extendedTextMessageData', {}).get('text') or "").strip()

    if not user_msg or user_msg.startswith(("🤖", "📊", "📽️", "⏳", "✅", "🧬")):
        return jsonify({"status": "ignored"}), 200

    is_admin_chat = (wid and chat_id == wid)
    registered = sb_request("GET", "users_and_roles", query=f"?phone_or_chat_id=eq.{chat_id}")
    is_lab_group = len(registered) > 0

    if user_msg == "تفعيل" and "@g.us" in chat_id:
        sb_request("POST", "users_and_roles", {
            "phone_or_chat_id": chat_id,
            "user_name": "أحمد عز الدين (شريك علم البيانات)",
            "role": "co_lead",
            "specialty": "Data Science, Python, Excel, Power BI, Balady"
        })
        send_msg(chat_id, "✅ *تم تفعيل مختبر Albaraa Ai os بنجاح!*\nمرحباً بك يا أ. أحمد عز الدين.\nجميع وحدات (علم البيانات، Python، Power BI، Excel، منصة بلدي، ومشاريع الأكاديمية) جاهزة لخدمتك الآن، وبيانات الأداء والتطور مربوطة بالذاكرة السحابية.")
        return jsonify({"status": "lab_activated"}), 200

    if not is_admin_chat and not is_lab_group:
        return jsonify({"status": "unauthorized"}), 200

    role = "admin" if is_admin_chat else "co_lead"
    low = user_msg.lower()

    if is_admin_chat and user_msg.startswith(("ابن وكيل", "انشئ وكيل", "أنشئ وكيل")):
        spec = call_groq(f"صمم تعريف وكيل ذكي بناءً على: {user_msg}", 'أعد JSON فقط: {"unit": "الوحدة", "name": "اسم الوكيل", "subs": "3 مساعدين", "prompt": "التعليمات"}')
        try:
            ag = json.loads(spec[spec.find("{"):spec.rfind("}") + 1])
            sb_request("POST", "agents_registry", {
                "unit_name": ag.get("unit", "وحدة مخصصة"),
                "agent_name": ag.get("name", "وكيل جديد"),
                "sub_agents": ag.get("subs", "3 مساعدين"),
                "system_prompt": ag.get("prompt", user_msg)
            })
            send_msg(chat_id, f"🧬 *مصنع الوكلاء (Agent Factory):*\nتم بناء وتفعيل الوكيل الجديد وحفظه في الذاكرة السحابية!\n• *الاسم:* {ag.get('name')}\n• *الوحدة:* {ag.get('unit')}\n• *المساعدون:* {ag.get('subs')}")
        except Exception:
            send_msg(chat_id, "✅ تم تسجيل الوكيل الجديد في الذاكرة السحابية.")
        return jsonify({"status": "agent_created"}), 200

    if is_admin_chat and any(k in low for k in ("تقرير القياس", "جدول القياس", "احصائيات")):
        logs = sb_request("GET", "telemetry_kpis", query="?order=id.desc&limit=50")
        rows = list()
        rows.append(("رقم العملية", "الدور", "الوحدة المستخدمة", "زمن الاستجابة (ث)", "الوقت الموفر (دقيقة)", "مؤشر تطور المستخدم", "نوع المخرج"))
        for item in logs:
            rows.append((item.get("id"), item.get("user_role"), item.get("unit_used"), item.get("response_time_sec"), item.get("time_saved_min"), item.get("user_growth_score"), item.get("deliverable_type")))
        build_excel(chat_id, "", custom_rows=rows, title="جدول القياس العلمي وتطور المستخدم - Albaraa Ai os")
        return jsonify({"status": "kpi_sent"}), 200

    deliverable = "تقرير استشاري"
    if any(k in low for k in ("عرض", "بوربوينت", "شرائح", "pptx")):
        send_msg(chat_id, "⏳ جاري تصميم العرض التقديمي عبر وحدة المخرجات...")
        try:
            build_pptx(chat_id, user_msg)
            deliverable = "PowerPoint"
        except Exception:
            send_msg(chat_id, "تعذر توليد العرض، يرجى تبسيط الطلب.")
    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")):

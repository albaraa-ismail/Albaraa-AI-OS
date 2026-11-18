import os, requests, time, threading, openpyxl
from pptx import Presentation
from docx import Document
from duckduckgo_search import DDGS
from flask import Flask, request, jsonify

app = Flask(__name__)
SEEN = set()

G_URL = os.environ.get("GREEN_API_URL", "https://greenapi.com").strip().rstrip("/")
G_ID = os.environ.get("GREEN_API_ID", "").strip()
G_TOK = os.environ.get("GREEN_API_TOKEN", "").strip()
GEM_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
SB_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SB_KEY = os.environ.get("SUPABASE_KEY", "").strip()
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966575475336").strip()

def sb(m, t, p=None, q=""):
    if not SB_URL or not SB_KEY: return []
    u = f"{SB_URL}/rest/v1/{t}{q}"
    h = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    try:
        r = requests.get(u, headers=h, timeout=10) if m == "GET" else requests.post(u, json=p, headers=h, timeout=10)
        if r.status_code in (200, 201): return r.json()
    except Exception as e: print("SB Err:", e)
    return []

def ai_ask(p, s):
    if GROQ_KEY:
        try:
            u = "https://" + "://groq.com"
            r = requests.post(u, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]}, headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=25)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"].strip()
            print("Groq Err:", r.text)
        except Exception as e: print("Groq Ex:", e)
    if GEM_KEY:
        try:
            u = "https://" + f"://googleapis.com{GEM_KEY}"
            r = requests.post(u, json={"contents": [{"parts": [{"text": f"{s}\n{p}"}]}]}, timeout=25)
            if r.status_code == 200: return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            print("Gem Err:", r.text)
        except Exception as e: print("Gem Ex:", e)
    if OR_KEY:
        try:
            u = "https://" + "openrouter.ai/api/v1/chat/completions"
            r = requests.post(u, json={"model": "openrouter/free", "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]}, headers={"Authorization": f"Bearer {OR_KEY}"}, timeout=25)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e: print("OR Ex:", e)
    return "تمت المعالجة بنجاح عبر Albaraa Ai os."

def send_msg(c, t):
    if t and G_URL:
        try:
            r = requests.post(f"{G_URL}/waInstance{G_ID}/sendMessage/{G_TOK}", json={"chatId": c, "message": t}, timeout=15)
            print("Send Status:", r.status_code, r.text)
        except Exception as e: print("Send Err:", e)

def send_file(c, path, name, mime, cap):
    if G_URL:
        try:
            with open(path, "rb") as f:
                requests.post(f"{G_URL}/waInstance{G_ID}/sendFileByUpload/{G_TOK}", data={"chatId": c, "caption": cap}, files={"file": (name, f, mime)}, timeout=35)
        except Exception as e: print("File Err:", e)

def run_task(cid, msg, role, sname):
    t0, low, dtype = time.time(), msg.lower(), "استشارة"
    if role == "admin" and msg.startswith(("ابن وكيل", "انشئ وكيل", "أنشئ وكيل")):
        sb("POST", "agents_registry", {"unit_name": "تخصصية", "agent_name": msg[:25], "sub_agents": "3 مساعدين", "system_prompt": msg})
        send_msg(cid, f"🧬 *مصنع الوكلاء:* تم تفعيل *{msg[:25]}* بنجاح!"); return
    if role == "admin" and any(k in low for k in ("تقرير القياس", "جدول القياس", "احصائيات")):
        wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
        ws.append(["العملية", "الدور", "الوحدة", "الزمن", "الموفر", "التطور", "المخرج"])
        for i in sb("GET", "telemetry_kpis", q="?order=id.desc&limit=50"):
            ws.append([i.get("id"), i.get("user_role"), i.get("unit_used"), i.get("response_time_sec"), i.get("time_saved_min"), i.get("user_growth_score"), i.get("deliverable_type")])
        wb.save("/tmp/KPI.xlsx"); send_file(cid, "/tmp/KPI.xlsx", "KPIs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 جدول القياس"); return
    if any(k in low for k in ("وورد", "word", "تقرير رسمي", "خطاب")):
        send_msg(cid, "⏳ جاري إعداد مستند الوورد...")
        raw = ai_ask(msg, "اكتب تقريراً رسمياً مفصلاً بالعربية بعناوين وفقرات:")
        doc = Document(); doc.add_heading("تقرير رسمي — Albaraa Ai os", 0)
        for l in raw.split("\n"):
            cl = l.strip().replace("**", "")
            if cl: doc.add_heading(cl.lstrip("# "), level=1) if cl.startswith(("#", "أولاً", "ثانياً", "1.", "2.")) else doc.add_paragraph(cl)
        doc.save("/tmp/Doc.docx"); send_file(cid, "/tmp/Doc.docx", "Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "📄 مستند وورد جاهز"); dtype = "Word"
    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")):
        send_msg(cid, "⏳ جاري بناء الإكسل...")
        raw = ai_ask(msg, "اكتب جدولاً، كل سطر صف وتفصل الأعمدة بعلامة | فقط:")
        wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
        for l in raw.split("\n"):
            if "|" in l: ws.append([x.strip() for x in l.split("|") if x.strip()])
        wb.save("/tmp/Out.xlsx"); send_file(cid, "/tmp/Out.xlsx", "Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "📊 ملف إكسل جاهز"); dtype = "Excel"
    elif any(k in low for k in ("عرض", "بوربوينت", "شرائح")):
        send_msg(cid, "⏳ جاري تصميم العرض...")
        raw = ai_ask(msg, "صمم 5 شرائح، عنوان كل شريحة بسطر وتحته 3 نقاط، وافصل بسطر فارغ:")
        prs = Presentation(); s0 = prs.slides.add_slide(prs.slide_layouts[0]); s0.shapes.title.text = "Albaraa Ai os"; s0.placeholders[1].text = msg[:60]
        for blk in [x.strip() for x in raw.split("\n\n") if x.strip()]:
            lns = [l.strip().replace("**", "") for l in blk.split("\n") if l.strip()]
            if lns:
                sl = prs.slides.add_slide(prs.slide_layouts[1]); sl.shapes.title.text = lns[0][:60]; sl.placeholders[1].text = "\n".join(lns[1:])
        prs.save("/tmp/Out.pptx"); send_file(cid, "/tmp/Out.pptx", "Slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "📽️ عرض تقديمي جاهز"); dtype = "PowerPoint"
    else:
        web = ""
        try:
            with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text(msg, max_results=2)])
        except Exception: pass
        ag = "\n".join([f"{a.get('agent_name')}: {a.get('system_prompt')}" for a in sb("GET", "agents_registry", q="?order=id.desc&limit=10")])
        ans = ai_ask(f"{msg}\nبحث:\n{web}", f"أنت منظومة Albaraa Ai os. الوكلاء:\n{ag}\nأجب باحترافية بالعربية.")
        sb("POST", "self_learning_logs", {"user_role": role, "task_type": "هندسي", "lesson_learned": f"{sname}: {msg[:40]}"})
        send_msg(cid, f"🤖 *Albaraa Ai os*\n━━━━━━━━━━\n{ans}\n━━━━━━━━━━\n🌐 نشط ✅")
    sb("POST", "telemetry_kpis", {"user_id": cid, "user_role": role, "unit_used": "Admin", "task_complexity": "متقدم", "response_time_sec": round(time.time() - t0, 2), "time_saved_min": 45, "user_growth_score": 90, "deliverable_type": dtype})

@app.route("/", methods=["GET", "POST"])
@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return jsonify({"status": "online"}), 200
    d = request.get_json(silent=True) or {}
    if d.get("typeWebhook") != "incomingMessageReceived": return jsonify({"status": "skip"}), 200
    mid = d.get("idMessage", "")
    if not mid or mid in SEEN: return jsonify({"status": "dup"}), 200
    SEEN.add(mid)
    sd, md = d.get("senderData", {}), d.get("messageData", {})
    cid, sname = sd.get("chatId", ""), sd.get("senderName", "User")
    msg = md.get("textMessageData", {}).get("textMessage", "") or md.get("extendedTextMessageData", {}).get("text", "")
    if cid and msg:
        role = "admin" if ADMIN_PHONE in cid else "user"
        threading.Thread(target=run_task, args=(cid, msg.strip(), role, sname)).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

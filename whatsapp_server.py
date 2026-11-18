import os, time, threading, openpyxl
from pptx import Presentation
from docx import Document
from duckduckgo_search import DDGS
from flask import Flask, request, jsonify
from core_ai import sb, ai_ask, send_msg, send_file

app = Flask(__name__)
SEEN = set()
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "966575475336").strip()

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
        prs = Presentation(); s0 = prs.slides.add_slide(prs.slide_layouts); s0.shapes.title.text = "Albaraa Ai os"; s0.placeholders.text = msg[:60]
        for blk in [x.strip() for x in raw.split("\n\n") if x.strip()]:
            lns = [l.strip().replace("**", "") for l in blk.split("\n") if l.strip()]
            if lns:
                sl = prs.slides.add_slide(prs.slide_layouts); sl.shapes.title.text = lns[:60]; sl.placeholders.text = "\n".join(lns[1:])
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

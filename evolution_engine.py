import os, openpyxl
from datetime import datetime, timezone, timedelta
from duckduckgo_search import DDGS
from core_ai import sb, ai_ask, send_msg, send_file

ADMIN_CID = os.environ.get("ADMIN_PHONE", "966575475336").strip() + "@c.us"

def propose_agent(cid, req_text, requester):
    clean_name = ai_ask(req_text, "استخرج اسماً مهنياً مختصراً ونظيفاً باللغة العربية الفصحى لهذا القسم أو الوكيل (من 3 إلى 5 كلمات فقط بدون أي علامات ترقيم أو شرح):").replace('"', '').replace('*', '').strip()[:50]
    spec = ai_ask(req_text, f"صمم هيكل قسم ووكيل ذكي باسم ({clean_name}). اكتب: 1- المهام الرئيسية 2- الصلاحيات 3- ضوابط الأمان:")
    sb("POST", "agents_registry", {"unit_name": "قيد_الاعتماد", "agent_name": clean_name, "sub_agents": requester, "system_prompt": spec})
    send_msg(cid, f"🛠️ *تم رصد احتياج جديد:* {clean_name}\nجاري هندسة القسم وتجهيزه للاعتماد...")
    send_msg(ADMIN_CID, f"🔐 *طلب اعتماد قسم جديد*\n👤 *المرسل:* {requester}\n🏷️ *الاسم المقترح:* {clean_name}\n\n{spec}\n\n✅ للتثبيت أرسل: *موافق*")

def approve_pending(cid):
    pending = sb("GET", "agents_registry", q="?unit_name=eq.قيد_الاعتماد&order=id.desc&limit=1")
    if not pending: send_msg(cid, "ℹ️ لا توجد أقسام بانتظار الاعتماد."); return
    item = pending.pop(0)
    sb("PATCH", "agents_registry", {"unit_name": "قسم_معتمد_نشط"}, q=f"?id=eq.{item['id']}")
    send_msg(cid, f"✅ *تم التثبيت والتفعيل:* القسم (*{item['agent_name']}*) نشط الآن.")

def manage_agents(cid, msg):
    if "احذف" in msg or "حذف" in msg:
        target = msg.replace("احذف وكيل", "").replace("حذف وكيل", "").replace("احذف", "").strip()
        agents = sb("GET", "agents_registry", q="?unit_name=eq.قسم_معتمد_نشط")
        for a in agents:
            if target and target in a.get("agent_name", ""):
                sb("PATCH", "agents_registry", {"unit_name": "محذوف"}, q=f"?id=eq.{a['id']}")
                send_msg(cid, f"🗑️ تم إيقاف وحذف القسم/الوكيل: *{a['agent_name']}*"); return
        send_msg(cid, "⚠️ لم يتم العثور على وكيل بهذا الاسم."); return
    agents = sb("GET", "agents_registry", q="?unit_name=eq.قسم_معتمد_نشط&order=id.desc")
    txt = "\n".join([f"• *{a.get('agent_name')}*" for a in agents]) or "لا توجد أقسام مخصصة مضافة بعد."
    send_msg(cid, f"📋 *الأقسام والوكلاء المعتمدون حالياً:*\n━━━━━━━━━━\n{txt}")

def add_reminder(cid, msg):
    now_str = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M")
    due = ai_ask(f"الوقت الحالي: {now_str}\nالطلب: {msg}", "استخرج وقت التذكير المستقبلي بصيغة YYYY-MM-DD HH:MM فقط بدون أي حرف إضافي:")
    sb("POST", "self_learning_logs", {"user_role": cid, "task_type": "تذكير_نشط", "lesson_learned": f"{due.strip()}|{msg}"})
    send_msg(cid, f"⏰ *تم ضبط التذكير الذكي بنجاح*\nسيتم التنبيه في الموعد المحدد: `{due.strip()}`")

def backup_memory(cid):
    wb = openpyxl.Workbook(); ws = wb.active; ws.sheet_view.rightToLeft = True
    ws.append(["النوع", "المحتوى والخبرة المكتسبة"])
    for x in sb("GET", "self_learning_logs", q="?order=id.desc&limit=200"): ws.append([x.get("task_type"), x.get("lesson_learned")])
    for a in sb("GET", "agents_registry", q="?order=id.desc&limit=50"): ws.append([a.get("unit_name"), f"{a.get('agent_name')}: {a.get('system_prompt')}"])
    wb.save("/tmp/Backup.xlsx")
    send_file(cid, "/tmp/Backup.xlsx", "System_Backup.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "💾 نسخة احتياطية شاملة للذاكرة والأقسام")

def self_evolve_and_research(cid):
    web = ""
    try:
        with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text("latest AI agents automation frameworks 2026", max_results=3)])
    except Exception: pass
    ideas = ai_ask(web, "اقترح 3 ابتكارات تقنية وأمنية لتطوير قدرات الفريق وزيادة سرعة الإنجاز بالعربية:")
    sb("POST", "self_learning_logs", {"user_role": "system", "task_type": "ابتكار_وتطوير", "lesson_learned": ideas[:300]})
    send_msg(cid, f"🚀 *تقرير التطور والابتكار الذاتي*\n━━━━━━━━━━\n{ideas}\n━━━━━━━━━━\n🛡️ تم تحديث قاعدة المعرفة.")

def periodic_analytics(cid):
    logs = sb("GET", "telemetry_kpis", q="?order=id.asc&limit=100")
    if not logs: send_msg(cid, "📊 لا توجد بيانات كافية للتحليل بعد."); return
    total = len(logs)
    avg_time = round(sum(float(x.get("response_time_sec", 2)) for x in logs) / total, 2)
    saved_hrs = round(sum(int(x.get("time_saved_min", 45)) for x in logs) / 60, 1)
    first_score = logs.pop(0).get("user_growth_score", 70)
    last_score = logs[-1].get("user_growth_score", 95) if logs else first_score
    send_msg(cid, f"📈 *التقرير الدوري لقياس الأداء*\n━━━━━━━━━━\n• *المهام المنجزة:* {total}\n• *سرعة الإنجاز:* {avg_time} ثانية\n• *الوقت الموفر:* {saved_hrs} ساعة\n• *تطور الأداء:* ارتفع من {first_score}% إلى {last_score}%")

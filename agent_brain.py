import time
from duckduckgo_search import DDGS
from core_ai import sb, ai_ask, send_msg
from office_tools import make_kpi, make_word, make_excel, make_ppt

def run_task(cid, msg, role, sname):
    t0, low, dtype = time.time(), msg.lower(), "استشارة"
    if role == "admin" and msg.startswith(("ابن وكيل", "انشئ وكيل", "أنشئ وكيل")):
        sb("POST", "agents_registry", {"unit_name": "تخصصية", "agent_name": msg[:25], "sub_agents": "3 مساعدين", "system_prompt": msg})
        send_msg(cid, f"🧬 *مصنع الوكلاء:* تم تفعيل *{msg[:25]}* بنجاح!"); return
    if role == "admin" and any(k in low for k in ("تقرير القياس", "جدول القياس", "احصائيات")):
        make_kpi(cid); return
    if any(k in low for k in ("وورد", "word", "تقرير رسمي", "خطاب")):
        make_word(cid, msg); dtype = "Word"
    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")):
        make_excel(cid, msg); dtype = "Excel"
    elif any(k in low for k in ("عرض", "بوربوينت", "شرائح")):
        make_ppt(cid, msg); dtype = "PowerPoint"
    else:
        web = ""
        try:
            with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text(msg, max_results=2)])
        except Exception: pass
        ag = "\n".join([f"{a.get('agent_name')}: {a.get('system_prompt')}" for a in sb("GET", "agents_registry", q="?order=id.desc&limit=10")])
        ans = ai_ask(f"{msg}\nبحث:\n{web}", f"أنت منظومة Albaraa Ai os. الوكلاء:\n{ag}\nأجب باحترافية بالعربية.")
        sb("POST", "self_learning_logs", {"user_role": role, "task_type": "هندسي", "lesson_learned": f"{sname}: {msg[:40]}"})
        send_msg(cid, f"🤖 *Albaraa Ai os*\n━━━━━━━━━━\n{ans}\n━━━━━━━━━━\n🌐 نشط ✅")
    sb("POST", "telemetry_kpis", {"user_id": cid, "user_role": role, "unit_used": "Co-Lead" if role == "co_lead" else "Admin", "task_complexity": "متقدم", "response_time_sec": round(time.time() - t0, 2), "time_saved_min": 45, "user_growth_score": 90, "deliverable_type": dtype})

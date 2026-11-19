import time, json, pendulum
from hijridate import Gregorian
from duckduckgo_search import DDGS
from core_ai import sb, ai_ask, send_msg
from office_tools import make_kpi, make_word, make_excel
from media_maker import make_ppt, make_video
from memory_engine import get_context, save_memory
from evolution_engine import propose_agent, approve_pending, manage_agents, add_reminder, backup_memory, self_evolve_and_research, periodic_analytics

def _time_ctx():
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ ({now.format('YYYY/MM/DD - hh:mm A')})"

def _plan_mission(msg):
    p = (
        f'أنت الوكيل القائد. حلل الهدف وحدد خطة الوكلاء بصيغة JSON فقط:\n'
        f'{{"deliverable": "word|excel|ppt|video|report", "search_query": "كلمات البحث", "steps": ["خطوة 1", "خطوة 2", "خطوة 3"]}}\n'
        f'الهدف: {msg}'
    )
    res = ai_ask(p, "أخرج JSON صالح فقط بدون أي نص إضافي.")
    try: return json.loads(res[res.find("{"):res.rfind("}")+1])
    except Exception: return {"deliverable": "report", "search_query": msg[:40], "steps": ["تحليل الهدف", "جمع البيانات", "إصدار المخرج التنفيذي"]}

def run_task(cid, msg, role, sname):
    print("MISSION START:", cid, msg[:25])
    t0, low, dtype = time.time(), msg.lower(), "مخرج تنفيذي"

    if role == "admin" and any(k in low for k in ("موافق", "اعتماد", "اعتمد", "ثبت")): approve_pending(cid); return
    if role == "admin" and any(k in low for k in ("اعرض الوكلاء", "الوكلاء المعتمدين", "احذف وكيل", "حذف وكيل")): manage_agents(cid, msg); return
    if role == "admin" and any(k in low for k in ("نسخة احتياطية", "نسخه احتياطيه")): backup_memory(cid); return
    if role == "admin" and any(k in low for k in ("تقرير دوري", "قياس الأداء", "تحليل السلوك")): periodic_analytics(cid); return
    if role == "admin" and any(k in low for k in ("جدول القياس", "احصائيات اكسل")): make_kpi(cid); return
    if role == "admin" and any(k in low for k in ("طور نفسك", "ابحث عن الجديد", "ابتكار")): self_evolve_and_research(cid); return
    if any(k in low for k in ("ذكرني", "ذكرنا", "تذكير", "موعد")): add_reminder(cid, msg); return
    if any(w in low for w in ("وكيل", "قسم")) and any(v in low for v in ("ابن", "أبن", "ابني", "أبني", "انشئ", "أنشئ", "سوي", "اعمل", "جديد")):
        propose_agent(cid, msg, sname); return

    send_msg(cid, "🧭 *غرفة عمليات الوكلاء:* تم استلام الهدف، الوكيل القائد يحلل المتطلبات ويوزع المهام...")

    plan = _plan_mission(msg)
    deliv = plan.get("deliverable", "report")
    if any(k in low for k in ("فيديو", "فديو", "مقطع", "video")): deliv = "video"
    elif any(k in low for k in ("عرض", "بوربوينت", "شرائح")): deliv = "ppt"
    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول", "لوحة تحكم")): deliv = "excel"
    elif any(k in low for k in ("وورد", "word", "بحث", "تقرير رسمي")): deliv = "word"

    if deliv == "video": make_video(cid, msg); dtype = "Video"
    elif deliv == "word": make_word(cid, msg); dtype = "Word"
    elif deliv == "excel": make_excel(cid, msg); dtype = "Excel"
    elif deliv == "ppt": make_ppt(cid, msg); dtype = "PowerPoint"
    else:
        steps_txt = " ⬅️ ".join(plan.get("steps", [])[:3])
        web = ""
        try:
            with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text(plan.get("search_query", msg), max_results=3)])
        except Exception: pass

        ctx = get_context(cid)
        ags = "\n".join([f"- {a.get('agent_name')}: {a.get('system_prompt')}" for a in sb("GET", "agents_registry", q="?unit_name=eq.قسم_معتمد_نشط&order=id.desc&limit=10")])

        raw_work = ai_ask(
            f"التوقيت: {_time_ctx()}\nالمهمة: {msg}\nخطة التنفيذ: {steps_txt}\nالذاكرة:\n{ctx}\nبيانات البحث:\n{web}",
            f"أنت فريق الوكلاء التنفيذيين:\n{ags}\nأنجز المهمة كمخرج مؤسسي متكامل ومنظم بعناوين وجداول نصية وتوصيات عملية."
        )
        governed = ai_ask(
            f"المهمة الأصلية: {msg}\nمخرج فريق الإنتاج:\n{raw_work}",
            "أنت وكيل الحوكمة وضمان الجودة. دقق المخرج، ارفع جودته التنفيذية، واختم بـ [التوصية التنفيذية التالية]. يُحظر ذكر أي اسم منظومة."
        )
        final_report = f"📑 *مخرج منظومة الوكلاء المعتمد*\n━━━━━━━━━━\n{governed}"
        save_memory(cid, role, sname, msg, final_report)
        send_msg(cid, final_report)

    growth = min(99, 85 + len(sb("GET", "telemetry_kpis", q=f"?user_id=eq.{cid}&limit=15")))
    sb("POST", "telemetry_kpis", {"user_id": cid, "user_role": role, "unit_used": "منظومة الوكلاء", "task_complexity": "متقدم", "response_time_sec": round(time.time() - t0, 2), "time_saved_min": 45, "user_growth_score": growth, "deliverable_type": dtype})

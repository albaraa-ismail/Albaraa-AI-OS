import time, pendulum
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
    return f"التاريخ الهجري: {h.day}/{h.month}/{h.year}هـ | الميلادي: {now.format('YYYY/MM/DD')} | الوقت: {now.format('hh:mm A')}"

def run_task(cid, msg, role, sname):
    t0, low, dtype = time.time(), msg.lower(), "مهمة ذكية"
    if role == "admin" and any(k in low for k in ("موافق", "اعتماد", "اعتمد", "ثبت")): approve_pending(cid); return
    if role == "admin" and any(k in low for k in ("اعرض الوكلاء", "الوكلاء المعتمدين", "احذف وكيل", "حذف وكيل")): manage_agents(cid, msg); return
    if role == "admin" and any(k in low for k in ("نسخة احتياطية", "نسخه احتياطيه")): backup_memory(cid); return
    if role == "admin" and any(k in low for k in ("تقرير دوري", "قياس الأداء", "تحليل السلوك")): periodic_analytics(cid); return
    if role == "admin" and any(k in low for k in ("جدول القياس", "احصائيات اكسل")): make_kpi(cid); return
    if role == "admin" and any(k in low for k in ("طور نفسك", "ابحث عن الجديد", "ابتكار")): self_evolve_and_research(cid); return
    if any(k in low for k in ("ذكرني", "ذكرنا", "تذكير", "موعد")): add_reminder(cid, msg); return
    if any(w in low for w in ("وكيل", "قسم")) and any(v in low for v in ("ابن", "أبن", "ابني", "أبني", "أبنى", "انشئ", "أنشئ", "سوي", "اعمل", "نحتاج", "جديد")):
        propose_agent(cid, msg, sname); return

    if any(k in low for k in ("فيديو", "فديو", "مقطع", "video")): make_video(cid, msg); dtype = "Video"
    elif any(k in low for k in ("وورد", "word", "تقرير رسمي", "خطاب", "بحث")): make_word(cid, msg); dtype = "Word"
    elif any(k in low for k in ("اكسل", "إكسل", "excel", "جدول")): make_excel(cid, msg); dtype = "Excel"
    elif any(k in low for k in ("عرض", "بوربوينت", "شرائح")): make_ppt(cid, msg); dtype = "PowerPoint"
    else:
        web = ""
        if any(k in low for k in ("ابحث", "بحث", "اخبار", "أخبار", "سعر", "اليوم", "2026", "كم", "متى")):
            try:
                with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text(msg, max_results=3)])
            except Exception: pass
        ctx = get_context(cid)
        ag = "\n".join([f"- {a.get('agent_name')}: {a.get('system_prompt')}" for a in sb("GET", "agents_registry", q="?unit_name=eq.قسم_معتمد_نشط&order=id.desc&limit=10")])
        draft = ai_ask(f"الزمن: {_time_ctx()}\nالطلب: {msg}\nالسياق:\n{ctx}\nبحث:\n{web}", f"أنت فريق عمل تنفيذي متكامل. الأقسام المتاحة:\n{ag}\nنفذ الطلب بدقة واحترافية عالية بالعربية.")
        if len(draft) > 400:
            ans = ai_ask(f"الطلب: {msg}\nالمسودة:\n{draft}", "أنت مدقق جودة تنفيذي. راجع المسودة وحسّن صياغتها لتكون دقيقة واحترافية ومباشرة دون ذكر أي اسم منظومة أو ذكاء اصطناعي.")
        else:
            ans = draft
        save_memory(cid, role, sname, msg, ans)
        send_msg(cid, ans)

    growth = min(99, 85 + len(sb("GET", "telemetry_kpis", q=f"?user_id=eq.{cid}&limit=15")))
    sb("POST", "telemetry_kpis", {"user_id": cid, "user_role": role, "unit_used": "فريق العمل" if role == "co_lead" else "الإدارة", "task_complexity": "متقدم", "response_time_sec": round(time.time() - t0, 2), "time_saved_min": 45, "user_growth_score": growth, "deliverable_type": dtype})

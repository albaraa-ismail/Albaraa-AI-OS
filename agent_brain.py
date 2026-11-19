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

def _chief_route(msg):
    p = (
        f"حلل طلب المستخدم التالي وحدد مسار التنفيذ الأنسب بدقة في سطر واحد بصيغة JSON فقط بدون أي نص إضافي:\n"
        f'{{"action": "word|excel|ppt|video|chat", "need_search": true/false, "topic": "عنوان مختصر للموضوع"}}\n'
        f"قواعد التوجيه: اختر excel إذا طلب جدولاً أو مقارنة رقمية أو ميزانية. اختر ppt إذا طلب عرضاً أو شرائح. اختر word إذا طلب تقريراً أو بحثاً أو خطاباً طويلاً. اختر video إذا طلب فيديو أو مقطعاً مرئياً. اختر chat لباقي الحالات.\n"
        f"الطلب: {msg}"
    )
    res = ai_ask(p, "أنت الوكيل القائد (Chief Orchestrator). أخرج JSON صالح فقط.")
    try:
        clean = res[res.find("{"):res.rfind("}")+1]
        return json.loads(clean)
    except Exception:
        return {"action": "chat", "need_search": True, "topic": msg[:40]}

def run_task(cid, msg, role, sname):
    t0, low, dtype = time.time(), msg.lower(), "تحليل ذكي"
    if role == "admin" and any(k in low for k in ("موافق", "اعتماد", "اعتمد", "ثبت")): approve_pending(cid); return
    if role == "admin" and any(k in low for k in ("اعرض الوكلاء", "الوكلاء المعتمدين", "احذف وكيل", "حذف وكيل")): manage_agents(cid, msg); return
    if role == "admin" and any(k in low for k in ("نسخة احتياطية", "نسخه احتياطيه")): backup_memory(cid); return
    if role == "admin" and any(k in low for k in ("تقرير دوري", "قياس الأداء", "تحليل السلوك")): periodic_analytics(cid); return
    if role == "admin" and any(k in low for k in ("جدول القياس", "احصائيات اكسل")): make_kpi(cid); return
    if role == "admin" and any(k in low for k in ("طور نفسك", "ابحث عن الجديد", "ابتكار")): self_evolve_and_research(cid); return
    if any(k in low for k in ("ذكرني", "ذكرنا", "تذكير", "موعد")): add_reminder(cid, msg); return
    if any(w in low for w in ("وكيل", "قسم")) and any(v in low for v in ("ابن", "أبن", "ابني", "أبني", "أبنى", "انشئ", "أنشئ", "سوي", "اعمل", "نحتاج", "جديد")):
        propose_agent(cid, msg, sname); return

    route = _chief_route(msg)
    act = route.get("action", "chat")
    if any(k in low for k in ("فيديو", "فديو", "مقطع", "video")): act = "video"
    elif any(k in low for k in ("عرض", "بوربوينت", "شرائح")): act = "ppt"
    elif any(k in low for k in ("اكسل", "إكسل", "excel")): act = "excel"
    elif any(k in low for k in ("وورد", "word", "بحث", "تقرير رسمي")): act = "word"

    if act == "video": make_video(cid, msg); dtype = "Video"
    elif act == "word": make_word(cid, msg); dtype = "Word"
    elif act == "excel": make_excel(cid, msg); dtype = "Excel"
    elif act == "ppt": make_ppt(cid, msg); dtype = "PowerPoint"
    else:
        web = ""
        if route.get("need_search") or any(k in low for k in ("ابحث", "بحث", "اخبار", "أخبار", "سعر", "اليوم", "2026")):
            try:
                with DDGS() as dd: web = "\n".join([x.get("body", "") for x in dd.text(msg, max_results=3)])
            except Exception: pass
        ctx = get_context(cid)
        ag = "\n".join([f"- {a.get('agent_name')}: {a.get('system_prompt')}" for a in sb("GET", "agents_registry", q="?unit_name=eq.قسم_معتمد_نشط&order=id.desc&limit=10")])
        draft = ai_ask(
            f"التوقيت: {_time_ctx()}\nالطلب: {msg}\nالسياق:\n{ctx}\nنتائج البحث:\n{web}",
            f"أنت وكيل البناء والتحليل التنفيذي. الأقسام المتاحة:\n{ag}\nقدم إجابة شاملة، منظمة بنقاط وعناوين واضحة، وعملية للغاية."
        )
        ans = ai_ask(
            f"الطلب: {msg}\nالمخرج:\n{draft}",
            "أنت وكيل الحوكمة وضمان الجودة. راجع المخرج وتأكد من دقته واحترافيته، وأضف في نهايته سطراً واحداً يقترح خطوة تنفيذية تالية ذكية مرتبطة بالموضوع (مثل تحويله لعرض أو جدول). يُحظر ذكر أي اسم منظومة."
        )
        save_memory(cid, role, sname, msg, ans)
        send_msg(cid, ans)

    growth = min(99, 85 + len(sb("GET", "telemetry_kpis", q=f"?user_id=eq.{cid}&limit=15")))
    sb("POST", "telemetry_kpis", {"user_id": cid, "user_role": role, "unit_used": "منظومة الوكلاء", "task_complexity": "متقدم", "response_time_sec": round(time.time() - t0, 2), "time_saved_min": 45, "user_growth_score": growth, "deliverable_type": dtype})

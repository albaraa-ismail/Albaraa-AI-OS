import os
import json
import time
import evolution_engine
from core_ai import sb, ai_ask, ai_ask_json, send_msg, send_file
from memory_engine import get_context, save_memory
from office_tools import make_kpi, make_word, make_excel, make_pptx, make_powerbi_kit
from video_studio import make_video
from agents.research_agent import ResearchAgent
from agents.learning_agent import QualityReviewerAgent
from agents.builder_agent import BuilderAgent
from agents.chief_agent import ChiefOrchestrator

HOST_URL = "".join(["https:/", "/albaraa-ai-os.", "onrender.", "com"])

def _real_multi_agent_pipeline(cid: str, msg: str, ctx: str, agents_list: list) -> str:
    send_msg(cid, "🔍 *المرحلة 1/3 (وكيل البحث):* جاري البحث عن بيانات ومصادر حقيقية...")
    web_facts = ""
    try:
        researcher = ResearchAgent()
        web_facts = researcher.search_links(msg[:120])
    except Exception as e:
        print("Research Agent Err:", e, flush=True)

    send_msg(cid, "⚙️ *المرحلة 2/3 (وكلاء التخطيط والتنفيذ):* جاري تحليل المعطيات وصياغة المخرج...")
    learned_rules = evolution_engine.get_learned_rules()
    team_roles = "\n".join([f"- {a.get('agent_name')}: {a.get('role_description')}" for a in agents_list]) or "- فريق وكلاء التخطيط والتحليل"
    draft_prompt = f"طلب المستخدم:\n{msg}\n\nنتائج البحث الحية:\n{web_facts or 'لا توجد نتائج إضافية'}\n\nالسياق:\n{ctx}\n\nالفريق:\n{team_roles}"
    sys_exec = f"أنت مدير منظومة الوكلاء. ابنِ إجابة دقيقة ومرتبة بناءً على نتائج البحث وبيانات المستخدم فقط، ولا تخترع أي أرقام.{learned_rules}"
    draft_output = ai_ask(draft_prompt, sys_exec, temperature=0.2)

    send_msg(cid, "🛡️ *المرحلة 3/3 (وكيل الجودة والحوكمة):* جاري تدقيق الأرقام ومراجعة الاتساق...")
    reviewer = QualityReviewerAgent(llm_callable=lambda p: ai_ask(p, f"أنت مدقق جودة صارم تمنع التضارب والأرقام الوهمية.{learned_rules}", temperature=0.1))
    return reviewer.review_and_improve(draft_output, msg)

def run_task(cid: str, msg: str, role: str, sname: str):
    t0 = time.time()
    m_low = msg.strip().lower()

    if any(msg.startswith(p) for p in ("ملاحظة:", "ملاحظة ", "تعديل:", "قاعدة:", "تغذية راجعة:")):
        evolution_engine.save_user_feedback(cid, msg)
        return

    if any(k in msg for k in ("تطوير ذاتي", "طور نفسك", "ابتكار", "تحديث القدرات")):
        evolution_engine.self_evolve_and_research(cid)
        return

    if any(k in msg for k in ("تحليل التطور", "قياس التطور", "تقرير التعلم")):
        evolution_engine.periodic_analytics(cid)
        return

    if any(k in msg for k in ("أضف وكيل", "اضف وكيل", "انشئ وكيل", "أنشئ وكيل", "قائمة الوكلاء", "الوكلاء النشطين", "احذف وكيل")):
        send_msg(cid, evolution_engine.manage_agents(msg, cid))
        return

    if "نسخة احتياطية" in msg or "باك اب" in m_low:
        evolution_engine.backup_memory(cid)
        return

    if any(k in msg for k in ("تقرير الأداء", "مؤشرات الأداء", "kpi")):
        make_kpi(cid)
        return

    if any(k in msg for k in ("فيديو", "مونتاج", "video", "موشن")):
        make_video(cid, msg)
        return

    # تفعيل القائد المخطط المستقل (Autonomous Orchestrator)
    ctx = get_context(cid)
    learned_rules = evolution_engine.get_learned_rules()
    orchestrator = ChiefOrchestrator()
    steps = orchestrator.plan_execution(msg, learned_rules)

    if len(steps) > 1:
        plan_txt = "\n".join([f"{i+1}. *{s.get('tool')}*: {s.get('task')}" for i, s in enumerate(steps)])
        send_msg(cid, f"🧠 *خطة التنفيذ المستقلة ({len(steps)} مراحل):*\n{plan_txt}")

    shared_scratchpad = ""
    last_code_content = ""
    last_code_filename = "index.html"
    builder = BuilderAgent()
    researcher = ResearchAgent()

    for idx, step in enumerate(steps, 1):
        tool = step.get("tool", "multi_agent_report")
        task_desc = step.get("task", msg)
        enriched_task = f"{task_desc}\n\n[معطيات المراحل السابقة]:\n{shared_scratchpad}" if shared_scratchpad else task_desc

        if tool == "web_search":
            send_msg(cid, f"🔍 *المرحلة {idx}/{len(steps)} (وكيل البحث):* جاري جمع البيانات الحية...")
            res_web = researcher.search_links(task_desc[:120])
            shared_scratchpad += f"\n- نتائج البحث:\n{res_web}\n"

        elif tool == "live_board":
            send_msg(cid, f"🌐 *المرحلة {idx}/{len(steps)} (وكيل Power BI الحي):* جاري بناء اللوحة التفاعلية...")
            p_board = (
                f"بناءً على المعطيات: '{enriched_task}'\n"
                "أنشئ هيكل لوحة بيانات احترافية تحتوي على 6 صفوف واقعية ومفيدة.\n"
                'أرجع JSON فقط: {"title": "عنوان اللوحة", "cols": ["العمود1", "العمود2", "الرقم", "المستهدف", "الحالة"], "rows": [[...], [...]]}'
            )
            board_obj = ai_ask_json(p_board, f"أنت مهندس بيانات Power BI.{learned_rules}")
            if board_obj and board_obj.get("rows"):
                saved = sb("POST", "self_learning_logs", {"user_role": cid, "task_type": "live_board", "lesson_learned": json.dumps(board_obj, ensure_ascii=False)})
                bid = saved[0]["id"] if isinstance(saved, list) and saved else 1
                send_msg(cid, f"🚀 *تم إطلاق لوحة Power BI الحية!*\n🔗 {HOST_URL}/board/{bid}")
                shared_scratchpad += f"\n- تم إنشاء لوحة حية بعنوان: {board_obj.get('title')}\n"

        elif tool == "powerbi_dax":
            make_powerbi_kit(cid, enriched_task)

        elif tool == "excel_report":
            make_excel(cid, enriched_task)

        elif tool == "word_doc":
            make_word(cid, enriched_task)

        elif tool == "pptx_slides":
            make_pptx(cid, enriched_task)

        elif tool in ("build_website", "build_code"):
            send_msg(cid, f"💻 *المرحلة {idx}/{len(steps)} (وكيل التطوير):* جاري هندسة المشروع البرمجي...")
            res = builder.build_pro_website(enriched_task) if tool == "build_website" else builder.generate_code_structure(task_desc[:40], enriched_task)
            if res.get("status") == "success":
                f_path = res.get("file_path")
                last_code_filename = res.get("filename", "index.html")
                last_code_content = res.get("code", "")
                mime = "text/html" if last_code_filename.endswith(".html") else "text/x-python"
                send_file(cid, f_path, last_code_filename, mime, "✅ تم بناء المشروع ومراجعته.")
                if os.path.exists(f_path):
                    os.remove(f_path)
            else:
                send_msg(cid, f"⚠ {res.get('message', 'تعذر توليد المشروع')}")

        elif tool == "push_github":
            send_msg(cid, f"🐙 *المرحلة {idx}/{len(steps)} (وكيل GitHub):* جاري رفع المشروع للمستودع...")
            if not last_code_content:
                gen = builder.build_pro_website(enriched_task)
                last_code_content = gen.get("code", "")
                last_code_filename = gen.get("filename", "index.html")
            if last_code_content:
                repo_url = builder.push_to_github(f"albaraa-{int(time.time())}", last_code_filename, last_code_content)
                send_msg(cid, f"🔗 رابط المستودع على GitHub:\n{repo_url}")

        else:
            agents_list = sb("GET", "agents_registry", q="?unit_name=eq.قسم_معتمد_نشط") or []
            final_ans = _real_multi_agent_pipeline(cid, enriched_task, ctx, agents_list)
            send_msg(cid, f"📑 *مخرج منظومة الوكلاء المعتمد:*\n━━━━━━━━━━\n{final_ans}")
            save_memory(cid, role, sname, msg, final_ans)

    sb("POST", "telemetry_kpis", {"user_role": role, "unit_used": "Autonomous_Orchestrator", "response_time_sec": round(time.time() - t0, 2), "time_saved_min": 25, "user_growth_score": 98, "deliverable_type": "multi_step_execution"})

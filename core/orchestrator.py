import time
from core.core_ai import ai_ask, ai_ask_json, send_msg, sb
from core.event_bus import BUS
from security.iam_gateway import IAM_GATEWAY
from security.safe_guard import inspect_prompt_injection
from security.vault_masking import PII_MASKER
from security.audit_ledger import AUDIT_LEDGER
from multimodal.arabic_nlp import normalize_arabic_dialect, polish_human_style
from intelligence.ml_intent_anomaly import INTENT_CLASSIFIER
from intelligence.rl_router import RL_ROUTER
from intelligence.research_agent import ResearchAgent
from intelligence.learning_agent import QualityReviewerAgent
from intelligence.builder_agent import BuilderAgent
from intelligence.memory_engine import get_context, save_memory
from telemetry.evolution_engine import log_kpi, spawn_dynamic_agent
from telemetry.realtime_monitor import MONITOR


class ChiefOrchestrator:
    """محرك التنسيق المركزي وإدارة المهام (النظم الخبيرة + التوجيه بالتعلم المعزز)."""

    def __init__(self):
        self.researcher = ResearchAgent()
        self.reviewer = QualityReviewerAgent(llm_callable=ai_ask)
        self.builder = BuilderAgent()

    def build_execution_plan(self, user_prompt: str, context: str = "") -> dict:
        sys_prompt = (
            "أنت المايسترو المنسق لمنظومة Albaraa-AI-OS. حلل طلب المستخدم وحدد خطة التنفيذ.\n"
            'أرجع JSON فقط بهذا الهيكل: {"intent": "research|code|analysis|general", '
            '"needs_web_search": true/false, "search_query": "استعلام بحث دقيق إن لزم", '
            '"subtasks": ["خطوة 1", "خطوة 2"]}'
        )
        plan = ai_ask_json(f"السياق:\n{context[:1200]}\n\nالطلب:\n{user_prompt[:1500]}", sys_prompt, mode="fast")
        if isinstance(plan, dict) and "intent" in plan:
            return plan
        return {"intent": "general", "needs_web_search": False, "search_query": "", "subtasks": [user_prompt[:300]]}

    def execute(self, cid: str, raw_msg: str, role: str = "admin", sname: str = "User", skip_research: bool = False) -> str:
        t0 = time.time()
        MONITOR.record_start("chief_orchestrator")
        BUS.publish("task.received", {"cid": cid, "role": role, "sender": sname})

        # 1. فحص الهوية وعزل البيانات (الوحدتان 3 و 4)
        session = IAM_GATEWAY.resolve_session(cid, role)
        if not session["authorized"]:
            AUDIT_LEDGER.append(cid, "ACCESS_DENIED", {"reason": "unauthorized_role"})
            return "⛔ عذراً، صلاحيات حسابك لا تسمح بتنفيذ هذا الطلب."

        # 2. درع الحماية من الاختراق النصي (الوحدة 7)
        safe_check = inspect_prompt_injection(raw_msg)
        if not safe_check["is_safe"]:
            AUDIT_LEDGER.append(cid, "PROMPT_INJECTION_BLOCKED", {"pattern": safe_check["matched_rule"]})
            send_msg(cid, f"🛡 *درع الحماية السيبراني:* تم صد محاولة حقن أو تجاوز صلاحيات ({safe_check['matched_rule']}).")
            return "Blocked by Security Shield."

        # 3. إخفاء البيانات الحساسة وتصحيح اللهجات (الوحدتان 9 و 11)
        masked_msg, pii_map = PII_MASKER.mask(raw_msg)
        clean_msg = normalize_arabic_dialect(masked_msg)

        # 4. مصنف النوايا وكشف الشذوذ بتعلّم الآلة + التوجيه بالتعلم المعزّز (الوحدتان 16 و 17)
        ml_pred = INTENT_CLASSIFIER.predict(clean_msg)
        if ml_pred["is_anomaly"]:
            AUDIT_LEDGER.append(cid, "ANOMALY_DETECTED", {"score": ml_pred["anomaly_score"]})

        chosen_agent = RL_ROUTER.select_agent(ml_pred["intent"], ["research", "builder", "general"])

        # 5. أمر إنشاء وكيل جديد ديناميكياً
        if any(k in clean_msg for k in ("انشئ وكيل", "أنشئ وكيل", "اصنع وكيل", "وكيل جديد")):
            res_spawn = spawn_dynamic_agent(clean_msg)
            AUDIT_LEDGER.append(cid, "AGENT_SPAWNED", {"request": clean_msg[:80]})
            send_msg(cid, res_spawn)
            MONITOR.record_end("chief_orchestrator", time.time() - t0, success=True)
            return res_spawn

        # 6. استرجاع الذاكرة الدلالية (الوحدة 20)
        memory_ctx = get_context(session["tenant_id"])
        plan = self.build_execution_plan(clean_msg, memory_ctx)

        # 7. تنفيذ البحث أو البرمجة أو التحليل (الوحدة 18)
        research_notes = ""
        if not skip_research and (plan.get("needs_web_search") or ml_pred["intent"] == "research" or chosen_agent == "research"):
            send_msg(cid, "🔍 *وكيل البحث والتفكير العميق:* جاري جمع البيانات وتدقيق المراجع...")
            q = plan.get("search_query") or clean_msg
            research_notes = self.researcher.deep_research(q)

        if ml_pred["intent"] == "code" or chosen_agent == "builder":
            send_msg(cid, "💻 *وكيل التطوير والبرمجة:* جاري هندسة الحل البرمجي...")
            draft = self.builder.build_solution(clean_msg, memory_ctx)
        else:
            sys_prompt = (
                "أنت منظومة Albaraa-AI-OS التنفيذية. أجب بدقة واحترافية ووضوح باللغة العربية.\n"
                "إذا توفرت مراجع بحثية فاستند إليها واذكرها بوضوح."
            )
            full_prompt = f"{memory_ctx}\n\n{research_notes}\n\nطلب المستخدم:\n{clean_msg}".strip()
            draft = ai_ask(full_prompt, sys_prompt, mode="arabic")

        # إيقاف المراجعة وحفظ الذاكرة في حال فشل التوليد الأساسي
        if not draft or draft.strip().startswith("⚠"):
            elapsed = round(time.time() - t0, 2)
            RL_ROUTER.update_reward(ml_pred["intent"], chosen_agent, -0.5)
            MONITOR.record_end("chief_orchestrator", elapsed, success=False)
            AUDIT_LEDGER.append(cid, "TASK_FAILED", {"agent": chosen_agent, "elapsed_sec": elapsed})
            err_msg = draft or "⚠ تعذر الحصول على استجابة من المحركات حالياً، يرجى إعادة المحاولة."
            send_msg(cid, err_msg)
            return err_msg

        # 8. المراجعة وتحسين الأسلوب البشري + استعادة البيانات المقنّعة (الوحدة 19)
        reviewed = self.reviewer.review_and_refine(clean_msg, draft)
        polished = polish_human_style(reviewed)
        final_answer = PII_MASKER.unmask(polished, pii_map)

        # 9. تحديث التعلم المعزّز، الذاكرة، الرصد، والتدقيق الجنائي (الوحدات 10، 17، 20، 23، 24)
        elapsed = round(time.time() - t0, 2)
        RL_ROUTER.update_reward(ml_pred["intent"], chosen_agent, 1.0)

        save_memory(session["tenant_id"], role, sname, raw_msg, final_answer)
        log_kpi(role, chosen_agent, elapsed, "text_response")
        MONITOR.record_end("chief_orchestrator", elapsed, success=True)
        AUDIT_LEDGER.append(cid, "TASK_COMPLETED", {"agent": chosen_agent, "elapsed_sec": elapsed})
        BUS.publish("task.completed", {"cid": cid, "agent": chosen_agent, "elapsed": elapsed})

        send_msg(cid, final_answer)
        return final_answer


ORCHESTRATOR = ChiefOrchestrator()


def run_task(cid: str, msg: str, role: str = "admin", sname: str = "User", skip_research: bool = False) -> str:
    """واجهة توافقية تحافظ على عمل جميع الاستدعاءات السابقة بسلاسة."""
    return ORCHESTRATOR.execute(cid, msg, role, sname, skip_research=skip_research)

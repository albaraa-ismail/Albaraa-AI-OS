import time
from typing import Any

from core.core_ai import ai_ask, ai_ask_json, send_msg
from core.event_bus import BUS
from intelligence.builder_agent import BuilderAgent
from intelligence.learning_agent import QualityReviewerAgent
from intelligence.memory_engine import get_context, save_memory
from intelligence.ml_intent_anomaly import INTENT_CLASSIFIER
from intelligence.research_agent import ResearchAgent
from intelligence.rl_router import RL_ROUTER
from multimodal.arabic_nlp import normalize_arabic_dialect, polish_human_style
from security.audit_ledger import AUDIT_LEDGER
from security.iam_gateway import IAM_GATEWAY
from security.safe_guard import inspect_prompt_injection
from security.vault_masking import PII_MASKER
from telemetry.evolution_engine import log_kpi, spawn_dynamic_agent
from telemetry.realtime_monitor import MONITOR

SPAWN_TRIGGERS = ("انشئ وكيل", "أنشئ وكيل", "اصنع وكيل", "وكيل جديد")

PLAN_SYSTEM_PROMPT = (
    "أنت المايسترو المنسق لمنظومة Albaraa-AI-OS. حلل طلب المستخدم وحدد خطة التنفيذ.\n"
    'أرجع JSON فقط بهذا الهيكل: {"intent": "research|code|analysis|general", '
    '"needs_web_search": true/false, "search_query": "استعلام بحث دقيق إن لزم", '
    '"subtasks": ["خطوة 1", "خطوة 2"]}'
)

EXEC_SYSTEM_PROMPT = (
    "أنت منظومة Albaraa-AI-OS التنفيذية. أجب بدقة واحترافية ووضوح باللغة العربية.\n"
    "إذا توفرت مراجع بحثية فاستند إليها واذكرها بوضوح."
)


class ChiefOrchestrator:
    """محرك التنسيق المركزي وإدارة المهام (النظم الخبيرة + التوجيه بالتعلم المعزز)."""

    def __init__(self) -> None:
        self.researcher = ResearchAgent()
        self.reviewer = QualityReviewerAgent(llm_callable=ai_ask)
        self.builder = BuilderAgent()

    def build_execution_plan(self, user_prompt: str, context: str = "") -> dict[str, Any]:
        """بناء خطة تنفيذ مهيكلة للمهام المعقدة أو البحثية."""
        plan = ai_ask_json(f"السياق:\n{context[:1200]}\n\nالطلب:\n{user_prompt[:1500]}", PLAN_SYSTEM_PROMPT, mode="fast")
        if isinstance(plan, dict) and "intent" in plan:
            return plan
        return {"intent": "general", "needs_web_search": False, "search_query": "", "subtasks": [user_prompt[:300]]}

    def _run_agent_pipeline(self, cid: str, clean_msg: str, memory_ctx: str, intent: str, agent: str, skip_research: bool) -> str:
        """توجيه التنفيذ للوكيل المختص (برمجة، بحث معمق، أو توليد مباشر)."""
        if intent == "code" or agent == "builder":
            send_msg(cid, "💻 *وكيل التطوير والبرمجة:* جاري هندسة الحل البرمجي...")
            return self.builder.build_solution(clean_msg, memory_ctx)

        needs_plan = len(clean_msg) > 60 or intent in ("research", "analysis") or agent == "research"
        plan = self.build_execution_plan(clean_msg, memory_ctx) if needs_plan else {"needs_web_search": False}

        research_notes = ""
        if not skip_research and (plan.get("needs_web_search") or intent == "research" or agent == "research"):
            send_msg(cid, "🔍 *وكيل البحث والتفكير العميق:* جاري جمع البيانات وتدقيق المراجع...")
            research_notes = self.researcher.deep_research(plan.get("search_query") or clean_msg)

        full_prompt = f"{memory_ctx}\n\n{research_notes}\n\nطلب المستخدم:\n{clean_msg}".strip()
        return ai_ask(full_prompt, EXEC_SYSTEM_PROMPT, mode="arabic")

    def execute(self, cid: str, raw_msg: str, role: str = "admin", sname: str = "User", skip_research: bool = False) -> str:
        t0 = time.time()
        MONITOR.record_start("chief_orchestrator")
        BUS.publish("task.received", {"cid": cid, "role": role, "sender": sname})

        # 1. التحقق من الهوية والصلاحيات
        session = IAM_GATEWAY.resolve_session(cid, role)
        if not session.get("authorized"):
            AUDIT_LEDGER.append(cid, "ACCESS_DENIED", {"reason": "unauthorized_role"})
            return "⛔ عذراً، صلاحيات حسابك لا تسمح بتنفيذ هذا الطلب."

        # 2. الفحص الأمني ومنع حقن الأوامر
        safe_check = inspect_prompt_injection(raw_msg)
        if not safe_check.get("is_safe"):
            AUDIT_LEDGER.append(cid, "PROMPT_INJECTION_BLOCKED", {"pattern": safe_check.get("matched_rule")})
            send_msg(cid, f"🛡 *درع الحماية السيبراني:* تم صد محاولة حقن أو تجاوز صلاحيات ({safe_check.get('matched_rule')}).")
            return "Blocked by Security Shield."

        # 3. إخفاء البيانات الحساسة وتطبيع النص
        masked_msg, pii_map = PII_MASKER.mask(raw_msg)
        clean_msg = normalize_arabic_dialect(masked_msg)

        # 4. تصنيف النوايا والتوجيه المعزز
        ml_pred = INTENT_CLASSIFIER.predict(clean_msg)
        if ml_pred.get("is_anomaly"):
            AUDIT_LEDGER.append(cid, "ANOMALY_DETECTED", {"score": ml_pred.get("anomaly_score")})

        intent = ml_pred.get("intent", "general")
        chosen_agent = RL_ROUTER.select_agent(intent, ["research", "builder", "general"])

        # 5. توليد وكيل ديناميكي عند الطلب
        if any(k in clean_msg for k in SPAWN_TRIGGERS):
            res_spawn = spawn_dynamic_agent(clean_msg)
            AUDIT_LEDGER.append(cid, "AGENT_SPAWNED", {"request": clean_msg[:80]})
            send_msg(cid, res_spawn)
            MONITOR.record_end("chief_orchestrator", time.time() - t0, success=True)
            return res_spawn

        # 6. تنفيذ المهمة عبر الوكيل المناسب
        memory_ctx = get_context(session["tenant_id"])
        draft = self._run_agent_pipeline(cid, clean_msg, memory_ctx, intent, chosen_agent, skip_research)

        if not draft or draft.strip().startswith("⚠"):
            elapsed = round(time.time() - t0, 2)
            RL_ROUTER.update_reward(intent, chosen_agent, -0.5)
            MONITOR.record_end("chief_orchestrator", elapsed, success=False)
            AUDIT_LEDGER.append(cid, "TASK_FAILED", {"agent": chosen_agent, "elapsed_sec": elapsed})
            err_msg = draft or "⚠ تعذر الحصول على استجابة من المحركات حالياً، يرجى إعادة المحاولة."
            send_msg(cid, err_msg)
            return err_msg

        # 7. المراجعة التحريرية للمخرجات الدسمة واستعادة البيانات المقنّعة
        reviewed = self.reviewer.review_and_refine(clean_msg, draft) if len(draft) > 450 else draft
        final_answer = PII_MASKER.unmask(polish_human_style(reviewed), pii_map)

        # 8. التحديث والتسجيل والمراقبة
        elapsed = round(time.time() - t0, 2)
        RL_ROUTER.update_reward(intent, chosen_agent, 1.0)
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

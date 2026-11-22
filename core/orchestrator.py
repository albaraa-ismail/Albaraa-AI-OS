import time
from typing import Any

from core.core_ai import ai_ask, send_msg
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
from security.safe_guard import apply_saudi_governance, inspect_prompt_injection
from security.vault_masking import PII_MASKER
from telemetry.evolution_engine import log_kpi
from telemetry.realtime_monitor import MONITOR


class ChiefOrchestrator:
    def __init__(self) -> None:
        self.researcher = ResearchAgent()
        self.builder = BuilderAgent()
        self.reviewer = QualityReviewerAgent(llm_callable=ai_ask)

    def build_execution_plan(self, goal: str, intent: str) -> str:
        sys_prompt = (
            "أنت المنسق التنفيذي الأعلى في منظومة Albaraa-AI-OS. "
            "ضع خطة عمل تنفيذية من 3 إلى 4 خطوات مرقمة ومختصرة باللغة العربية دون مقدمات."
        )
        return ai_ask(f"النية: {intent}\nالهدف: {goal}", sys_prompt, temperature=0.25, mode="fast")

    def execute(
        self,
        cid: str,
        raw_msg: str,
        role: str = "admin",
        sname: str = "User",
        notify_whatsapp: bool = True,
    ) -> str:
        t0 = time.time()
        MONITOR.record_start("chief_orchestrator")
        BUS.publish("task.received", {"cid": cid, "preview": raw_msg[:60]})

        try:
            session = IAM_GATEWAY.resolve_session(cid, requested_role=role)
            if not session["authorized"]:
                MONITOR.record_end("chief_orchestrator", time.time() - t0, success=False)
                return "عذرا، لا تملك صلاحية الوصول إلى هذه الوحدة."

            sec = inspect_prompt_injection(raw_msg, cid)
            if not sec["is_safe"]:
                AUDIT_LEDGER.append(cid, "SECURITY_BLOCK", {"rule": sec["matched_rule"]})
                MONITOR.record_end("chief_orchestrator", time.time() - t0, success=False)
                return "تم حظر هذا الطلب لمخالفته ضوابط الأمن السيبراني والحوكمة."

            masked_msg, pii_map = PII_MASKER.mask(raw_msg)
            normalized = normalize_arabic_dialect(masked_msg)

            ml_pred = INTENT_CLASSIFIER.predict(normalized)
            intent = ml_pred["intent"]
            if ml_pred["is_anomaly"]:
                AUDIT_LEDGER.append(cid, "ANOMALY_DETECTED", {"score": ml_pred["anomaly_score"]})

            candidates = ["research", "code", "general"]
            if intent in candidates:
                candidates = [intent] + [c for c in candidates if c != intent]
            chosen_agent = RL_ROUTER.select_agent(intent, candidates)

            memory_ctx = get_context(session["tenant_id"], normalized)
            plan = self.build_execution_plan(normalized, intent) if len(normalized) > 250 else ""

            if chosen_agent == "research" or intent == "research":
                raw_answer = self.researcher.deep_research(normalized)
            elif chosen_agent == "code" or intent == "code":
                raw_answer = self.builder.build_solution(normalized, context=memory_ctx)
            else:
                sys_prompt = (
                    "أنت العقل المدبر ومساعد الأعمال والبحث والتقنية في Albaraa-AI-OS. "
                    "أجب باللغة العربية الفصحى بأسلوب بشري واضح ومباشر ومنظم دون مقدمات آلية."
                )
                if memory_ctx:
                    sys_prompt += f"\n\n{memory_ctx}"
                prompt_body = f"خطة التنفيذ:\n{plan}\n\nالطلب:\n{normalized}" if plan else normalized
                raw_answer = ai_ask(prompt_body, sys_prompt, temperature=0.35, mode="arabic")

            if intent != "code" and len(raw_answer) > 550:
                raw_answer = self.reviewer.review_and_refine(normalized, raw_answer)

            styled = raw_answer if intent == "code" else polish_human_style(raw_answer)
            governed = apply_saudi_governance(normalized, styled)
            final_answer = PII_MASKER.unmask(governed, pii_map)

            elapsed = time.time() - t0
            reward = 1.0 if "⚠️" not in final_answer and len(final_answer) > 40 else 0.2
            RL_ROUTER.update_reward(intent, chosen_agent, reward)

            save_memory(session["tenant_id"], session["role"], sname, masked_msg, PII_MASKER.mask(final_answer)[0])
            log_kpi(session["role"], f"orchestrator:{chosen_agent}", elapsed, intent)
            AUDIT_LEDGER.append(session["tenant_id"], "TASK_COMPLETED", {"agent": chosen_agent, "sec": round(elapsed, 2)})
            MONITOR.record_end("chief_orchestrator", elapsed, success=True)
            BUS.publish("task.completed", {"cid": cid, "agent": chosen_agent, "elapsed": round(elapsed, 2)})

            if notify_whatsapp:
                send_msg(cid, final_answer)
            return final_answer

        except Exception as exc:
            elapsed = time.time() - t0
            MONITOR.record_end("chief_orchestrator", elapsed, success=False)
            AUDIT_LEDGER.append(cid, "TASK_FAILED", {"error": str(exc)[:120]})
            raise


ORCHESTRATOR = ChiefOrchestrator()


def run_task(
    cid: str,
    raw_msg: str,
    role: str = "admin",
    sname: str = "User",
    notify_whatsapp: bool = True,
) -> str:
    return ORCHESTRATOR.execute(cid, raw_msg, role=role, sname=sname, notify_whatsapp=notify_whatsapp)

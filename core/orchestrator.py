import time
from core.core_ai import ai_ask, send_msg
from core.event_bus import BUS
from intelligence.builder_agent import BuilderAgent
from intelligence.learning_agent import QualityReviewerAgent
from intelligence.memory_engine import get_context, save_memory
from intelligence.ml_intent_anomaly import INTENT_CLASSIFIER
from intelligence.research_agent import ResearchAgent
from intelligence.rl_router import RL_ROUTER
from multimodal.arabic_nlp import normalize_arabic_dialect, polish_human_style
from multimodal.office_tools import make_live_powerbi
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

    def _abort(self, cid: str, t0: float, event: str, meta: dict, reply: str) -> str:
        MONITOR.record_end("chief_orchestrator", time.time() - t0, success=False)
        AUDIT_LEDGER.append(cid, event, meta)
        return reply

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
            if not session.get("authorized"):
                return self._abort(cid, t0, "ACCESS_DENIED", {"role": role}, "عذراً، لا تملك صلاحية الوصول إلى هذه الوحدة.")

            sec = inspect_prompt_injection(raw_msg, cid)
            if not sec.get("is_safe", True):
                return self._abort(cid, t0, "SECURITY_BLOCK", {"rule": sec.get("matched_rule")}, "تم حظر هذا الطلب لمخالفته ضوابط الأمن السيبراني والحوكمة.")

            masked_msg, pii_map = PII_MASKER.mask(raw_msg)
            normalized = normalize_arabic_dialect(masked_msg)
            low_norm = normalized.lower()

            # توجيه مباشر لبناء لوحة تحكم تفاعلية حية إذا طُلبت داخل المحادثة
            if notify_whatsapp and any(k in low_norm for k in ("لوحة تحكم", "لوحة بيانات", "لوحه تحكم", "داشبورد", "dashboard")):
                make_live_powerbi(cid, normalized)
                elapsed = time.time() - t0
                log_kpi(session["role"], "orchestrator:live_dashboard", elapsed, "dashboard")
                MONITOR.record_end("chief_orchestrator", elapsed, success=True)
                return "✅ تم إنشاء لوحة التحكم التفاعلية الحية وإرسال رابطها."

            ml_pred = INTENT_CLASSIFIER.predict(normalized)
            intent = ml_pred.get("intent", "general")
            if ml_pred.get("is_anomaly"):
                AUDIT_LEDGER.append(cid, "ANOMALY_DETECTED", {"score": ml_pred.get("anomaly_score")})

            candidates = [intent] + [c for c in ("research", "code", "general") if c != intent] if intent in ("research", "code", "general") else ["general", "research", "code"]
            chosen_agent = RL_ROUTER.select_agent(intent, candidates)

            memory_ctx = get_context(session["tenant_id"], normalized)
            contextual_task = f"{normalized}\n\nسياق المحادثات السابقة:\n{memory_ctx}" if memory_ctx else normalized
            plan = self.build_execution_plan(normalized, intent) if len(normalized) > 200 else ""

            if chosen_agent == "research" or intent == "research":
                raw_answer = self.researcher.deep_research(contextual_task)
            elif chosen_agent == "code" or intent == "code":
                raw_answer = self.builder.build_solution(normalized, context=memory_ctx)
            else:
                sys_prompt = (
                    "أنت العقل المدبر ومساعد الأعمال والبحث والتقنية في منظومة Albaraa-AI-OS. "
                    "نفّذ طلب المستخدم مباشرة بأعلى جودة واحترافية باللغة العربية، مع أمثلة عملية وجداول منظمة. "
                    "إذا طلب المستخدم تنفيذ شيء نوقش سابقاً (مثل 'أنشئها الآن' أو 'نفذها')، فاعتمد على سياق المحادثات السابقة ونفذه فوراً دون طلب تفاصيل إضافية."
                    + (f"\n\n{memory_ctx}" if memory_ctx else "")
                )
                prompt_body = f"خطة التنفيذ:\n{plan}\n\nالطلب:\n{normalized}" if plan else normalized
                raw_answer = ai_ask(prompt_body, sys_prompt, temperature=0.35, mode="arabic", max_tokens=3000)

            if intent != "code" and len(raw_answer) > 900:
                raw_answer = self.reviewer.review_and_refine(normalized, raw_answer)

            styled = raw_answer if intent == "code" else polish_human_style(raw_answer)
            governed = apply_saudi_governance(normalized, styled)
            final_answer = PII_MASKER.unmask(governed, pii_map)

            elapsed = time.time() - t0
            reward = 1.0 if "⚠️" not in final_answer and "عذراً" not in final_answer and len(final_answer) > 40 else 0.2
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
            MONITOR.record_end("chief_orchestrator", time.time() - t0, success=False)
            AUDIT_LEDGER.append(cid, "TASK_FAILED", {"error": str(exc)[:120]})
            raise


ORCHESTRATOR = ChiefOrchestrator()


def run_task(cid: str, raw_msg: str, role: str = "admin", sname: str = "User", notify_whatsapp: bool = True) -> str:
    return ORCHESTRATOR.execute(cid, raw_msg, role=role, sname=sname, notify_whatsapp=notify_whatsapp)

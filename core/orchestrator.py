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

MARKET_RESEARCH_TRIGGERS = (
    "سوق", "منافس", "سعر", "أسعار", "تكلفة", "جدوى", "مشروع", "شركة", "نظام", "لائحة",
    "توطين", "زكاة", "ضريبة", "سلة", "زد", "تمويل", "استثمار", "دراسة", "خطة", "تقنية",
    "ذكاء اصطناعي", "تطبيق", "منصة", "السعودية", "الرياض", "بحث", "تحليل", "مقارنة",
)


def _fast_reviewer_llm(prompt: str, system: str = "", **kwargs) -> str:
    return ai_ask(prompt, system=system, temperature=0.2, mode="agent_fast", max_tokens=2200)


class ChiefOrchestrator:
    def __init__(self) -> None:
        self.researcher = ResearchAgent()
        self.builder = BuilderAgent()
        self.reviewer = QualityReviewerAgent(llm_callable=_fast_reviewer_llm)

    def _abort(self, cid: str, t0: float, event: str, meta: dict, reply: str) -> str:
        MONITOR.record_end("chief_orchestrator", time.time() - t0, success=False)
        AUDIT_LEDGER.append(cid, event, meta)
        return reply

    def _compress_context(self, text: str, max_chars: int = 1600) -> str:
        clean = (text or "").strip()
        return clean if len(clean) <= max_chars else clean[:max_chars] + "\n...[تم ضغط السياق لحفظ الموارد]"

    def _needs_market_research(self, text: str, intent: str) -> bool:
        if intent == "research":
            return True
        low = text.lower()
        return len(low) > 25 and any(k in low for k in MARKET_RESEARCH_TRIGGERS)

    def build_execution_plan(self, goal: str, intent: str, research_brief: str = "") -> str:
        sys_prompt = (
            "أنت المنسق التنفيذي الأعلى (Chief Planner) في منظومة Albaraa-AI-OS. "
            "حلل الهدف وبيانات البحث، وضع خطة عمل تنفيذية من 3 إلى 4 خطوات دقيقة تواكب متطلبات السوق السعودي دون أي مقدمات."
        )
        body = f"النية: {intent}\nالهدف: {goal}"
        if research_brief:
            body += f"\n\nمخرجات الوكيل الباحث:\n{self._compress_context(research_brief, 1200)}"
        return ai_ask(body, sys_prompt, temperature=0.2, mode="agent_fast", max_tokens=600)
    def _run_collaborative_pipeline(self, normalized: str, intent: str, chosen_agent: str, memory_ctx: str) -> tuple[str, list[str]]:
        active_agents: list[str] = []
        compact_mem = self._compress_context(memory_ctx, 1400)
        research_findings = ""

        # المرحلة 1: الوكيل الباحث يجمع حقائق السوق والأنظمة المحدثة عند الحاجة
        if self._needs_market_research(normalized, intent) or chosen_agent == "research":
            active_agents.append("ResearchAgent")
            query_with_ctx = f"{normalized}\n\nسياق ذو صلة:\n{compact_mem}" if compact_mem else normalized
            research_findings = self.researcher.deep_research(query_with_ctx)
            if intent == "research" and len(normalized) < 80 and not any(w in normalized for w in ("صمم", "ابني", "اكتب", "خطة", "دراسة", "كود")):
                return research_findings, active_agents

        # المرحلة 2: المنسق الأعلى يضع خطة التنفيذ باستخدام النموذج الخفيف المجاني
        plan = ""
        if len(normalized) > 60 or research_findings:
            active_agents.append("PlannerAgent")
            plan = self.build_execution_plan(normalized, intent, research_findings)

        # المرحلة 3: الوكيل المنفذ (المبرمج أو العقل المدبر التنفيذي) يبني الحل المتكامل
        if chosen_agent == "code" or intent == "code":
            active_agents.append("BuilderAgent")
            combined_ctx = "\n\n".join(p for p in (compact_mem, f"معطيات البحث:\n{self._compress_context(research_findings, 1500)}" if research_findings else "", f"خطة التنفيذ:\n{plan}" if plan else "") if p)
            raw_answer = self.builder.build_solution(normalized, context=combined_ctx)
        else:
            active_agents.append("ExecutiveAgent")
            sys_prompt = (
                "أنت العقل المدبر ومساعد الأعمال والبحث والتقنية في منظومة Albaraa-AI-OS. "
                "تعمل ضمن فريق وكلاء متعاونين لتقديم مخرجات احترافية جاهزة للسوق السعودي (متوافقة مع الأنظمة المحلية، الأسعار بالريال السعودي، وجداول وأمثلة عملية قابلة للتطبيق فوراً). "
                "إذا طلب المستخدم تنفيذ شيء نوقش سابقاً (مثل 'أنشئها الآن' أو 'نفذها')، فاعتمد على سياق المحادثات السابقة ونفذه فوراً دون طلب تفاصيل إضافية."
            )
            sections = [f"الطلب الأساسي:\n{normalized}"]
            if plan:
                sections.append(f"خطة التنفيذ المعتمدة:\n{plan}")
            if research_findings:
                sections.append(f"بيانات وحقائق الوكيل الباحث:\n{self._compress_context(research_findings, 1800)}")
            if compact_mem:
                sections.append(f"سياق المحادثات السابقة:\n{compact_mem}")

            raw_answer = ai_ask("\n\n".join(sections), sys_prompt, temperature=0.35, mode="agent_deep", max_tokens=3000)

        # المرحلة 4: وكيل التدقيق والجودة يراجع المخرج النهائي (دورة واحدة لحفظ الرصيد)
        if intent != "code" and len(raw_answer) > 750 and "⚠️" not in raw_answer:
            active_agents.append("QualityReviewerAgent")
            raw_answer = self.reviewer.review_and_refine(normalized, raw_answer)

        return raw_answer, active_agents

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

            raw_answer, active_agents = self._run_collaborative_pipeline(normalized, intent, chosen_agent, memory_ctx)

            styled = raw_answer if intent == "code" else polish_human_style(raw_answer)
            governed = apply_saudi_governance(normalized, styled)
            final_answer = PII_MASKER.unmask(governed, pii_map)

            elapsed = time.time() - t0
            reward = 1.0 if "⚠️" not in final_answer and "عذراً" not in final_answer and len(final_answer) > 40 else 0.2
            RL_ROUTER.update_reward(intent, chosen_agent, reward)

            agents_chain = " → ".join(active_agents) if active_agents else chosen_agent
            save_memory(session["tenant_id"], session["role"], sname, masked_msg, PII_MASKER.mask(final_answer)[0])
            log_kpi(session["role"], f"agents:{agents_chain}", elapsed, intent)
            AUDIT_LEDGER.append(session["tenant_id"], "AGENTS_COMPLETED", {"chain": agents_chain, "sec": round(elapsed, 2)})
            MONITOR.record_end("chief_orchestrator", elapsed, success=True)
            BUS.publish("task.completed", {"cid": cid, "agents": active_agents, "elapsed": round(elapsed, 2)})

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

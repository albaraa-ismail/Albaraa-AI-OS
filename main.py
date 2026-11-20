import os
import json
from core.orchestrator import ChiefOrchestrator
from core.event_bus import BUS
from security.iam_gateway import IAM_GATEWAY
from security.audit_ledger import AUDIT_LEDGER
from intelligence.ml_intent_anomaly import INTENT_CLASSIFIER
from intelligence.rl_router import RL_ROUTER
from telemetry.benchmark_lab import run_benchmark_suite
from telemetry.realtime_monitor import MONITOR


class MultiAgentSystem:
    """واجهة المحاكاة والتشغيل الموحدة لمنظومة Albaraa-AI-OS (25 وحدة)."""

    def __init__(self):
        self.orchestrator = ChiefOrchestrator()

    def run_live_demo(self, query: str, constraints: str = ""):
        print("\n--- تشغيل محاكاة Albaraa-AI-OS (25 وحدة متكاملة) ---")

        # 1. فحص الهوية والحوكمة
        session = IAM_GATEWAY.resolve_session("web_cli_admin", requested_role="admin")
        print(f"-> بوابة الهوية: الدور={session['role']} | المعرّف المعزول={session['tenant_id']}")

        # 2. تصنيف النوايا وكشف الشذوذ بتعلّم الآلة
        ml_pred = INTENT_CLASSIFIER.predict(query)
        print(f"-> مصنف النوايا ML: النية={ml_pred['intent']} (ثقة {ml_pred['confidence']*100:.0f}%)")

        # 3. اختبارات الجودة المعيارية (Benchmark Lab)
        bench = run_benchmark_suite()
        print(f"-> مختبر المقارنات المعيارية: الحالة={bench['status']} | زمن الاستجابة={bench['llm_latency_ms']}ms")

        # 4. تنفيذ المهمة عبر المنسق المركزي
        full_prompt = f"{query}\nالقيود والشروط: {constraints}".strip() if constraints else query
        reply = self.orchestrator.execute("web_cli_admin", full_prompt, role="admin", sname="Albaraa")

        # 5. حفظ التقرير والتدقيق الجنائي
        final_output = {
            "system": "Albaraa-AI-OS",
            "version": "3.0 (25 Modules)",
            "session": session,
            "ml_prediction": ml_pred,
            "rl_policy": RL_ROUTER.policy_snapshot(),
            "benchmark": bench,
            "telemetry": MONITOR.snapshot(),
            "forensic_integrity": AUDIT_LEDGER.verify_integrity(),
            "sample_output": reply[:300],
        }
        os.makedirs("shared_memory", exist_ok=True)
        with open("shared_memory/project_draft.txt", "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)

        BUS.publish("demo.completed", {"status": bench["status"]})
        print("--- تم حفظ التقرير الشامل في shared_memory/project_draft.txt ---")


if __name__ == "__main__":
    os_system = MultiAgentSystem()
    user_query = "البحث عن أدوات ذكاء اصطناعي لبناء المنصة وتوليد الأكواد"
    user_constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
    os_system.run_live_demo(user_query, user_constraints)

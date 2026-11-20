from core.core_ai import ai_ask


class BuilderAgent:
    """وكيل التطوير والهندسة البرمجية لبناء الأكواد والأنظمة المتكاملة."""

    def build_solution(self, task_prompt: str, context: str = "") -> str:
        sys_prompt = (
            "أنت مهندس برمجيات خبير في منظومة Albaraa-AI-OS. "
            "اكتب الكود كاملاً ومنظماً وجاهزاً للتشغيل المباشر بدون اختصار أو حذف، مع شرح خطوات التشغيل باختصار."
        )
        full_prompt = f"السياق التقني:\n{context}\n\nالمطلوب البرمجي:\n{task_prompt}".strip()
        return ai_ask(full_prompt, sys_prompt, temperature=0.2, mode="general")

class QualityReviewerAgent:
    """وكيل مراجعة الجودة والتحقق من اكتمال الإجابة قبل إرسالها للمستفيد."""

    def __init__(self, llm_callable=None):
        self.llm = llm_callable

    def review_and_refine(self, user_prompt: str, draft_answer: str) -> str:
        if not draft_answer or len(draft_answer.strip()) < 25 or "⚠" in draft_answer:
            return draft_answer
        if not self.llm:
            return draft_answer

        check_prompt = (
            f"طلب المستخدم الأصلي:\n{user_prompt}\n\n"
            f"المسودة المقترحة:\n{draft_answer}\n\n"
            "راجع المسودة: إذا كانت وافية ودقيقة ومنظمة أعدها كما هي محسّنة التنسيق، "
            "وإذا كان بها نقص أو غموض أكمله باحترافية باللغة العربية دون مقدمات:"
        )
        refined = self.llm(check_prompt, "أنت مدقق جودة تنفيذي في منظومة Albaraa-AI-OS.", temperature=0.25, mode="arabic")
        if refined and "⚠" not in refined and len(refined.strip()) > 20:
            return refined.strip()
        return draft_answer

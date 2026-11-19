class QualityReviewerAgent:
    def __init__(self, llm_callable=None, llm_call_function=None):
        self.llm = llm_callable or llm_call_function

    def review_and_improve(self, draft_response: str, user_request: str = "") -> str:
        if not draft_response or draft_response.startswith("⚠"):
            return draft_response
        if not self.llm:
            return draft_response

        review_prompt = (
            "أنت وكيل مراقبة الجودة والحوكمة (Self-Critic QA Agent) في نظام Albaraa-AI-OS.\n"
            f"طلب المستخدم: {user_request}\n"
            f"المسودة الأولية:\n{draft_response}\n\n"
            "المطلوب منك:\n"
            "1. منع أي أرقام وهمية أو تناقض في البيانات.\n"
            "2. إذا كان المخرج برمجياً: تأكد من اكتماله وخلوه من أي اختصارات.\n"
            "3. اجعل الصياغة العربية تنفيذية، واضحة، ومنظمة باحترافية عالية.\n"
            "4. أعد كتابة النسخة النهائية المعتمدة فقط بدون أي مقدمات."
        )
        improved = self.llm(review_prompt)
        return improved if (improved and not improved.startswith("⚠")) else draft_response

    def refine_output(self, user_request: str, draft_response: str) -> str:
        return self.review_and_improve(draft_response, user_request)

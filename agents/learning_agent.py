class QualityReviewerAgent:
    def __init__(self, llm_call_function):
        """
        llm_call_function: دالة استدعاء الذكاء الاصطناعي الموجودة في core_ai.py
        """
        self.llm = llm_call_function

    def refine_output(self, user_request: str, draft_response: str) -> str:
        """مراجعة المسودة وتطويرها لتكون بأعلى جودة ممكنة"""
        review_prompt = f"""
        أنت وكيل مراقبة الجودة (Quality Assurance Agent) في نظام Albaraa-AI-OS.
        طلب المستخدم الأصلي: {user_request}
        
        المسودة الأولية للرد:
        {draft_response}
        
        المطلوب منك:
        1. إذا كان الطلب برمجياً: تأكد من أن الكود كامل، خالٍ من الأخطاء، ولا يحتوي على اختصارات مثل (// أضف الكود هنا).
        2. إذا كان الطلب شرحاً أو خدمة: اجعل الصياغة احترافية، منظمة، ومباشرة.
        3. أعد كتابة النسخة النهائية المحسنة فقط بدون أي مقدمات منك.
        """
        return self.llm(review_prompt)

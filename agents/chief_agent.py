from agents.research_agent import ResearchAgent
from agents.learning_agent import QualityReviewerAgent
from office_tools import create_presentation
from whatsapp_server import send_whatsapp_message, send_whatsapp_file

class ChiefAgent:
    def __init__(self, llm_call_function):
        self.llm = llm_call_function
        self.researcher = ResearchAgent()
        self.reviewer = QualityReviewerAgent(llm_call_function)

    def handle_request(self, chat_id: str, user_message: str):
        # 1. طلب عرض تقديمي
        if "عرض تقديمي" in user_message or "بوربوينت" in user_message:
            send_whatsapp_message(chat_id, "⏳ جاري إعداد العرض التقديمي وتنسيقه...")
            prompt = f"""
            أنشئ محتوى عرض تقديمي احترافي حول: {user_message}.
            يجب أن يكون الرد بصيغة JSON فقط وبدون أي نص إضافي كالتالي:
            {{"title": "العنوان الرئيسي", "slides": [{{"heading": "عنوان الشريحة", "points": ["نقطة 1", "نقطة 2"]}}]}}
            """
            json_content = self.llm(prompt).replace("```json", "").replace("```", "").strip()
            file_path = create_presentation(json_content, "Albaraa_Presentation.pptx")
            send_whatsapp_file(chat_id, file_path, "✅ تفضل، العرض التقديمي جاهز.")
            return

        # 2. طلب روابط مواقع أو برامج
        if "رابط" in user_message or "روابط" in user_message or "برنامج" in user_message or "موقع" in user_message:
            send_whatsapp_message(chat_id, "🔍 جاري البحث والتحقق من الروابط...")
            links_result = self.researcher.search_links(user_message)
            send_whatsapp_message(chat_id, links_result)
            return

        # 3. أي خدمة أو كود برمجي آخر (مع تفعيل مراجعة الجودة)
        send_whatsapp_message(chat_id, "⚙️ جاري العمل على طلبك ومراجعة الجودة...")
        draft = self.llm(user_message)
        final_output = self.reviewer.refine_output(user_message, draft)
        send_whatsapp_message(chat_id, final_output)

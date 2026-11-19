from core_ai import ai_ask_json

class ChiefOrchestrator:
    def __init__(self):
        self.name = "القائد المخطط لمنظومة الوكلاء"

    def plan_execution(self, user_request: str, learned_rules: str = "") -> list:
        """يحلل طلب المستخدم المعقد ويقسّمه إلى خطوات عمل متسلسلة بأدوات حقيقية"""
        sys_prompt = (
            "أنت القائد المخطط (Chief AI Orchestrator) في نظام Albaraa-AI-OS.\n"
            "مهمتك فهم طلب المستخدم وتقسيمه إلى خطة عمل من خطوة واحدة إلى 4 خطوات متسلسلة.\n"
            "الأدوات المتاحة للفريق فقط هي:\n"
            "- web_search: للبحث عن معلومات حية وحديثة من الإنترنت.\n"
            "- live_board: لإنشاء لوحة تحكم Power BI تفاعلية حية على الويب.\n"
            "- powerbi_dax: لهندسة جداول البيانات ومعادلات DAX في ملف Word.\n"
            "- excel_report: لإنشاء ملف Excel احترافي ببطاقات مؤشرات ورسوم بيانية.\n"
            "- word_doc: لإنشاء تقرير Word تنفيذي مفصل.\n"
            "- pptx_slides: لتصميم عرض تقديمي PowerPoint احترافي.\n"
            "- build_website: لتصميم وبناء موقع ويب متكامل احترافي (HTML/Tailwind/Chart.js).\n"
            "- build_code: لكتابة سكربت برمجي Python متكامل.\n"
            "- push_github: لرفع المشروع أو الموقع أو الكود إلى مستودع GitHub.\n"
            "- multi_agent_report: للتحليل الاستراتيجي والإجابة الشاملة المدققة.\n\n"
            f"{learned_rules}\n"
            "أرجع كائن JSON فقط بهذا الهيكل الدقيق:\n"
            '{"steps": [{"tool": "اسم_الأداة", "task": "وصف دقيق للمطلوب في هذه الخطوة"}]}'
        )
        plan = ai_ask_json(f"طلب المستخدم:\n{user_request}", sys_prompt)
        steps = plan.get("steps", []) if isinstance(plan, dict) else []
        if not steps:
            return [{"tool": "multi_agent_report", "task": user_request}]
        return steps[:4]

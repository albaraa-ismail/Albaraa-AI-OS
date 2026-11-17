import os
import json

from agents.chief_agent import ChiefAgent
from agents.research_agent import ResearchAgent
from agents.builder_agent import BuilderAgent
from agents.project_manager_agent import ProjectManagerAgent
from agents.learning_agent import LearningAgent
from agents.career_agent import CareerAgent

class MultiAgentSystem:
    def __init__(self):
        # تهيئة الوكلاء
        self.chief = ChiefAgent()
        self.research = ResearchAgent()
        self.builder = BuilderAgent()
        self.governance = ProjectManagerAgent()
        self.trainer = LearningAgent()
        self.exporter = CareerAgent()
        
    def run_live_demo(self, query, constraints):
        print("\n--- تشغيل محاكاة Albaraa-AI-OS ---")
        
        # استلام المهمة وتنقيح الاستعلام
        init_status = self.chief.orchestrate_task(query, constraints)
        print(f"-> {init_status['orchestrator']}: تم استلام الطلب.")
        
        refined = self.research.refine_query(query, constraints)
        print(f"-> {self.research.name}: الاستعلام الجديد -> '{refined}'")
        
        # بيانات تجريبية للفحص
        mock_web_data = [
            {"name": "GitHub Copilot", "type": "Paid"},
            {"name": "VS Code Core", "type": "Free"},
            {"name": "Ollama Local LLM", "type": "Free"},
            {"name": "Replit Agent", "type": "Paid"}
        ]
        
        # فحص الأدوات وتطبيق الشروط
        approved, blocked = self.governance.audit_results(mock_web_data, constraints)
        print(f"-> {self.governance.name}:")
        print(f"   المعتمد: {[t['name'] for t in approved]}")
        print(f"   المحجوب: {[t['name'] for t in blocked]}")
        
        # بناء الهيكلية وتصدير التقرير
        build_log = self.builder.generate_code_structure("AI Agent Framework")
        print(f"-> {self.builder.name}: {build_log}")
        
        report_log = self.exporter.export_report(approved)
        print(f"-> {self.exporter.name}: {report_log}")
        
        # تقييم الأداء
        eval_log = self.trainer.evaluate_performance("Execution OK")
        print(f"-> {self.trainer.name}: الدقة -> {eval_log['accuracy']}")
        
        # حفظ المخرجات في الذاكرة
        final_output = {
            "system": "Albaraa-AI-OS",
            "approved": approved,
            "blocked": blocked,
            "evaluation": eval_log
        }
        os.makedirs("shared_memory", exist_ok=True)
        with open("shared_memory/project_draft.txt", "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
            
        print("--- تم حفظ التقرير في shared_memory/project_draft.txt ---")

if __name__ == "__main__":
    os_system = MultiAgentSystem()
    user_query = "البحث عن أدوات ذكاء اصطناعي لبناء المنصة وتوليد الأكواد"
    user_constraints = "الالتزام بالأدوات المجانية ومفتوحة المصدر فقط"
    
    os_system.run_live_demo(user_query, user_constraints)

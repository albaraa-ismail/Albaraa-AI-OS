import os
import json

# استدعاء الوكلاء الستة المطورين من مجلد agents
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
        print("\n==========================================")
        print("🚀 [النظام] جاري تشغيل بيئة المحاكاة الحية لـ Albaraa-Ai-os")
        print("==========================================\n")
        
        # 1. القائد يستقبل المهمة
        init_status = self.chief.orchestrate_task(query, constraints)
        print(f"-> {init_status['orchestrator']}: استلمت الطلب وبدأت التوجيه.\n")
        
        # 2. وكيل البحث ينقح الاستعلام ديناميكياً
        refined = self.research.refine_query(query, constraints)
        print(f"-> {self.research.name}: تم تنقيح وتوسيع الاستعلام إلى: '{refined}'\n")
        
        # 3. مصفوفة بيانات تجريبية (مفتوح ومغلق المصدر / مجاني ومدفوع)
        mock_web_data = [
            {"name": "GitHub Copilot", "type": "Paid"},
            {"name": "VS Code Core", "type": "Free"},
            {"name": "Ollama Local LLM", "type": "Free"},
            {"name": "Replit Agent", "type": "Paid"}
        ]
        
        # 4. وكيل الحوكمة يفحص الامتثال (النظام الخبير)
        approved, blocked = self.governance.audit_results(mock_web_data, constraints)
        print(f"-> {self.governance.name}: جاري تطبيق فلاتر الحوكمة الصارمة...")
        print(f"   [✓] الأدوات المعتمدة: {[t['name'] for t in approved]}")
        print(f"   [X] الأدوات المحجوبة: {[t['name'] for t in blocked]}\n")
        
        # 5. وكيل المطور يولد الهيكلية
        build_log = self.builder.generate_code_structure("AI Agent Framework")
        print(f"-> {self.builder.name}: {build_log}\n")
        
        # 6. وكيل التطبيقات يصدر التقرير النهائي
        report_log = self.exporter.export_report(approved)
        print(f"-> {self.exporter.name}: {report_log}")
        
        # 7. مدرب الأنظمة يقيم جودة العملية بالكامل
        eval_log = self.trainer.evaluate_performance("Execution OK")
        print(f"-> {self.trainer.name}: تم الفحص. الدقة المحققة: {eval_log['accuracy']}\n")
        
        # حفظ السجل النهائي في الذاكرة المشتركة
        final_output = {
            "system": "Albaraa-Ai-os",
            "approved": approved,
            "blocked": blocked,
            "evaluation": eval_log
        }
        os.makedirs("shared_memory", exist_ok=True)
        with open("shared_memory/project_draft.txt", "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
            
        print("==========================================")
        print("💾 [النظام] تم حفظ تقرير العمليات بنجاح في shared_memory/project_draft.txt")
        print("==========================================")

if __name__ == "__main__":
    # تشغيل السيناريو الفعلي المطابق لشروط تخرجك وهدفك التجاري
    os_system = MultiAgentSystem()
    user_query = "البحث عن أدوات ذكاء اصطناعي لبناء المنصة وتوليد الأكواد"
    user_constraints = "يجب الالتزام بالأدوات المجانية ومفتوحة المصدر فقط واستبعاد المدفوع"
    
    os_system.run_live_demo(user_query, user_constraints)

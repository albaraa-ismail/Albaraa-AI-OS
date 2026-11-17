class BuilderAgent:
    def __init__(self):
        self.name = "وكيل تطوير النظام"
        
    # توليد الهيكل البرمجي للمهمة
    def generate_code_structure(self, task_name):
        return f"// تم توليد الهيكل البرمجي لـ {task_name} بواسطة {self.name}"

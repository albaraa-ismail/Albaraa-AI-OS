import os
from core_ai import ai_ask

class BuilderAgent:
    def __init__(self):
        self.name = "وكيل تطوير النظام"

    def generate_code_structure(self, task_name: str, requirements: str = "") -> dict:
        """
        يولّد كوداً برمجياً حقيقياً عبر الذكاء الاصطناعي ويحفظه كملف قابل للتشغيل
        """
        sys_prompt = (
            "أنت مهندس برمجيات خبير في Python. "
            "اكتب الكود البرمجي الكامل والنظيف مباشرة بدون أي مقدمات أو شروحات أو علامات markdown."
        )
        prompt = f"المهمة البرمجية: {task_name}\nالمتطلبات التفصيلية: {requirements}"

        try:
            raw_code = ai_ask(prompt, sys_prompt, temperature=0.2)
            if raw_code.startswith("⚠"):
                return {"status": "error", "message": raw_code}

            clean_code = raw_code.replace("```python", "").replace("```", "").strip()
            os.makedirs("/tmp/generated_projects", exist_ok=True)
            safe_name = "".join(c if c.isalnum() else "_" for c in task_name)[:25] or "script"
            file_path = f"/tmp/generated_projects/{safe_name}.py"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(clean_code)

            return {
                "status": "success",
                "agent": self.name,
                "file_path": file_path,
                "code": clean_code
            }
        except Exception as e:
            return {"status": "error", "message": f"خطأ في بناء الكود: {str(e)}"}

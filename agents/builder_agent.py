import os
import base64
import requests
from core_ai import ai_ask

class BuilderAgent:
    def __init__(self):
        self.name = "وكيل التطوير والويب وGitHub"
        self.gh_token = os.environ.get("GITHUB_TOKEN", "").strip()

    def build_pro_website(self, requirements: str) -> dict:
        sys_prompt = (
            "أنت كبير مصممي ومطوري واجهات الويب (Senior UI/UX & Frontend Architect). "
            "قم ببناء صفحة ويب كاملة في ملف HTML واحد احترافي للغاية باللغة العربية (dir='rtl'). "
            "استخدم Tailwind CSS عبر CDN وخط Cairo من Google Fonts و Chart.js للرسوم البيانية التفاعلية. "
            "اجعل التصميم فخماً (وضع داكن Dark Mode متدرج، بطاقات زجاجية Glassmorphism، أزرار تفاعلية، وجداول قابلة للبحث). "
            "أرجع كود HTML الكامل فقط بدءاً من <!DOCTYPE html> بدون أي مقدمات أو شروحات."
        )
        raw = ai_ask(f"صمم موقعاً احترافياً متكاملاً للمتطلب التالي:\n{requirements}", sys_prompt, temperature=0.25)
        if raw.startswith("⚠"):
            return {"status": "error", "message": raw}

        clean_html = raw.replace("```html", "").replace("```", "").strip()
        os.makedirs("/tmp/generated_projects", exist_ok=True)
        file_path = "/tmp/generated_projects/index.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_html)

        return {"status": "success", "file_path": file_path, "code": clean_html, "filename": "index.html"}

    def generate_code_structure(self, task_name: str, requirements: str = "") -> dict:
        is_web = any(k in (task_name + requirements).lower() for k in ("موقع", "صفحة", "html", "واجهة", "landing", "web", "داشبورد"))
        if is_web:
            return self.build_pro_website(requirements or task_name)

        sys_prompt = "أنت مهندس برمجيات وبيانات خبير. اكتب الكود الكامل والنظيف مباشرة بدون مقدمات أو علامات markdown."
        raw_code = ai_ask(f"المهمة: {task_name}\nالمتطلبات: {requirements}", sys_prompt, temperature=0.2)
        if raw_code.startswith("⚠"):
            return {"status": "error", "message": raw_code}

        clean_code = raw_code.replace("```python", "").replace("```", "").strip()
        os.makedirs("/tmp/generated_projects", exist_ok=True)
        safe_name = "".join(c if c.isalnum() else "_" for c in task_name)[:25] or "solution"
        file_path = f"/tmp/generated_projects/{safe_name}.py"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_code)

        return {"status": "success", "file_path": file_path, "code": clean_code, "filename": f"{safe_name}.py"}

    def push_to_github(self, repo_name: str, file_path_in_repo: str, content: str, commit_msg: str = "AI Agent Auto-Commit") -> str:
        if not self.gh_token:
            return "⚠️ يرجى إضافة متغير GITHUB_TOKEN في إعدادات Render لتفعيل الرفع التلقائي على GitHub."

        headers = {"Authorization": f"token {self.gh_token}", "Accept": "application/vnd.github.v3+json"}
        u_res = requests.get("https://github.com", headers=headers, timeout=15)
        if u_res.status_code != 200:
            return f"⚠️ فشل التحقق من حساب GitHub: {u_res.status_code}"
        username = u_res.json().get("login")

        clean_repo = "".join(c if c.isalnum() or c == "-" else "-" for c in repo_name.lower()).strip("-") or "ai-agent-project"
        requests.post("https://github.comrepos", headers=headers, json={"name": clean_repo, "auto_init": True, "private": False}, timeout=15)

        api_url = f"https://github.com{username}/{clean_repo}/contents/{file_path_in_repo}"
        sha = None
        check = requests.get(api_url, headers=headers, timeout=15)
        if check.status_code == 200:
            sha = check.json().get("sha")

        payload = {"message": commit_msg, "content": base64.b64encode(content.encode("utf-8")).decode("utf-8")}
        if sha:
            payload["sha"] = sha

        put_res = requests.put(api_url, headers=headers, json=payload, timeout=20)
        if put_res.status_code in (200, 201):
            return f"https://github.com{username}/{clean_repo}"
        return f"⚠️ تعذر رفع الملف لـ GitHub: {put_res.status_code}"
 
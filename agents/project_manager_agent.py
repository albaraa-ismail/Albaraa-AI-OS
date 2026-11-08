class ProjectManagerAgent:
    def __init__(self):
        self.name = "وكيل الحوكمة والتشريعات"
        
    def audit_results(self, web_results, constraints):
        approved = []
        blocked = []
        for tool in web_results:
            if tool["type"] == "Free":
                approved.append(tool)
            else:
                blocked.append({"name": tool["name"], "reason": "محجوب: أداة مدفوعة مخالفة لشروط المسودة"})
        return approved, blocked

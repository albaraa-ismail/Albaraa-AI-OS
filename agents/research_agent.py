class ResearchAgent:
    def __init__(self):
        self.name = "وكيل البحث الذكي"
        
    def refine_query(self, base_query, constraints):
        refined = base_query
        if "مفتوحة المصدر" in constraints:
            refined += " + open-source github repository"
        if "مجانية" in constraints:
            refined += " + free tier"
        return refined

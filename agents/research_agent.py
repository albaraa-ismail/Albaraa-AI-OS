import requests
from duckduckgo_search import DDGS

class ResearchAgent:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def verify_url(self, url: str) -> bool:
        """التأكد من أن الرابط حقيقي ويعمل"""
        try:
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except Exception:
            return False

    def search_links(self, query: str, max_results: int = 5) -> str:
        """البحث عن روابط مواقع وبرامج حقيقية وموثوقة"""
        verified_results = []
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results + 3))
                for r in results:
                    url = r.get("href")
                    title = r.get("title")
                    snippet = r.get("body")
                    if url and self.verify_url(url):
                        verified_results.append(f"🔗 *{title}*\nالرابط: {url}\nالوصف: {snippet}\n")
                    if len(verified_results) >= max_results:
                        break
        except Exception as e:
            return f"حدث خطأ أثناء البحث: {str(e)}"

        if not verified_results:
            return "لم يتم العثور على روابط شغالة مطابقة لطلبك."

        return "✅ *النتائج والروابط الموثقة:*\n\n" + "\n".join(verified_results)

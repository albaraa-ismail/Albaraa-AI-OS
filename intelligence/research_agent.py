from typing import Dict, List
from core.core_ai import ai_ask

try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None

RESEARCH_SYSTEM_PROMPT = (
    "أنت مدقق مراجع وباحث أكاديمي. لخص الحقائق المؤكدة من المصادر أعلاه "
    "مع إرفاق رقم المرجع [1] أو [2] ورابطه الموثق."
)


class ResearchAgent:
    """وكيل التفكير العميق ومدقق المراجع (Deep Reasoning & Citation Verifier)."""

    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """تنفيذ بحث حي في الويب وإرجاع قائمة مهيكلة بالنتائج."""
        if DDGS is None:
            print("Search Err: duckduckgo_search library is not installed.", flush=True)
            return []

        try:
            with DDGS() as ddgs:
                raw_results = ddgs.text(query, max_results=max_results)
                return [
                    {
                        "title": item.get("title", "").strip(),
                        "href": item.get("href", "").strip(),
                        "body": item.get("body", "").strip(),
                    }
                    for item in raw_results
                ]
        except Exception as exc:
            print(f"Search Err: {exc}", flush=True)
            return []

    @staticmethod
    def _format_evidence(sources: List[Dict[str, str]]) -> str:
        """تنسيق المصادر كسياق خام لتغذية نموذج الذكاء الاصطناعي."""
        return "\n".join(
            f"[{idx}] {src['title']} ({src['href']})\n    ملخص: {src['body']}"
            for idx, src in enumerate(sources, 1)
        )

    @staticmethod
    def _format_citations(sources: List[Dict[str, str]]) -> str:
        """بناء قائمة المراجع النهائية القابلة للقراءة."""
        return "\n".join(
            f"- [{idx}] {src['title']}: {src['href']}"
            for idx, src in enumerate(sources, 1)
        )

    def deep_research(self, query: str, max_results: int = 5) -> str:
        """إجراء بحث معمق وتلخيص الحقائق مع توثيق المراجع."""
        sources = self.search_web(query, max_results=max_results)
        if not sources:
            return "لم يتم العثور على مصادر ويب مباشرة حالياً؛ اعتمد على المعرفة الأساسية الموثوقة."

        raw_evidence = self._format_evidence(sources)
        synthesis = ai_ask(
            prompt=f"السؤال البحثي: {query}\n\nالمصادر المسترجعة:\n{raw_evidence}",
            system=RESEARCH_SYSTEM_PROMPT,
            mode="arabic",
        )

        citations = self._format_citations(sources)
        return f"📚 *نتائج البحث وتدقيق المراجع:*\n{synthesis}\n\n🔗 *المصادر:*\n{citations}"

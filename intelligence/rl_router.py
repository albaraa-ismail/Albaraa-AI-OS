import re
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
    "مع إرفاق رقم المرجع [1] أو [2] ورابطه الموثق بالعربية الفصحى."
)


class ResearchAgent:
    def search_web(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        if DDGS is None:
            return []
        clean_q = re.sub(r"\[REDACTED_[A-Z_]+_\d+\]", "", query).strip()
        if not clean_q:
            return []
        try:
            with DDGS() as ddgs:
                raw_results = ddgs.text(clean_q, max_results=max_results)
                return [
                    {
                        "title": str(item.get("title", "")).strip(),
                        "href": str(item.get("href", "")).strip(),
                        "body": str(item.get("body", "")).strip(),
                    }
                    for item in raw_results
                    if item.get("body")
                ]
        except Exception as exc:
            print(f"Search Err: {exc}", flush=True)
            return []

    @staticmethod
    def _format_evidence(sources: list[dict[str, str]]) -> str:
        return "\n".join(
            f"[{idx}] {src['title']} ({src['href']})\n    ملخص: {src['body']}"
            for idx, src in enumerate(sources, 1)
        )

    @staticmethod
    def _format_citations(sources: list[dict[str, str]]) -> str:
        return "\n".join(
            f"- [{idx}] {src['title']}: {src['href']}"
            for idx, src in enumerate(sources, 1)
        )

    def deep_research(self, query: str, max_results: int = 5) -> str:
        sources = self.search_web(query, max_results=max_results)
        if not sources:
            fallback = ai_ask(
                query,
                "أنت باحث ومحلل معرفي خبير. أجب بدقة وموضوعية وتنظيم بالعربية الفصحى دون مقدمات آلية:",
                mode="arabic",
            )
            return f"📚 *التحليل المعرفي والبحثي:*\n{fallback}"

        raw_evidence = self._format_evidence(sources)
        synthesis = ai_ask(
            prompt=f"السؤال البحثي: {query}\n\nالمصادر المسترجعة:\n{raw_evidence}",
            system=RESEARCH_SYSTEM_PROMPT,
            mode="arabic",
        )
        citations = self._format_citations(sources)
        return f"📚 *نتائج البحث وتدقيق المراجع:*\n{synthesis}\n\n🔗 *المصادر:*\n{citations}"

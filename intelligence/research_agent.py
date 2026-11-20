from typing import List, Dict
from duckduckgo_search import DDGS
from core.core_ai import ai_ask


class ResearchAgent:
    """وكيل التفكير العميق ومدقق المراجع (Deep Reasoning & Citation Verifier)."""

    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        try:
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": item.get("title", "").strip(),
                        "href": item.get("href", "").strip(),
                        "body": item.get("body", "").strip(),
                    })
        except Exception as exc:
            print(f"Search Err: {exc}", flush=True)
        return results

    def deep_research(self, query: str) -> str:
        sources = self.search_web(query, max_results=5)
        if not sources:
            return "لم يتم العثور على مصادر ويب مباشرة حالياً؛ اعتمد على المعرفة الأساسية الموثوقة."

        formatted_sources = []
        for idx, s in enumerate(sources, 1):
            formatted_sources.append(f"[{idx}] {s['title']} ({s['href']})\n    ملخص: {s['body']}")

        raw_evidence = "\n".join(formatted_sources)
        synthesis = ai_ask(
            f"السؤال البحثي: {query}\n\nالمصادر المسترجعة:\n{raw_evidence}",
            "أنت مدقق مراجع وباحث أكاديمي. لخص الحقائق المؤكدة من المصادر أعلاه مع إرفاق رقم المرجع [1] أو [2] ورابطه الموثق.",
            mode="arabic",
        )
        return f"📚 *نتائج البحث وتدقيق المراجع:*\n{synthesis}\n\n🔗 *المصادر:*\n" + "\n".join(
            f"- [{i}] {s['title']}: {s['href']}" for i, s in enumerate(sources, 1)
        )

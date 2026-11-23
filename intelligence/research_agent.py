from concurrent.futures import ThreadPoolExecutor
from typing import Any
import httpx
import pendulum
from bs4 import BeautifulSoup
from hijridate import Gregorian
from core.core_ai import ai_ask

try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _today_stamp() -> str:
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ ({now.format('YYYY-MM-DD')}م)"


def _scrape_url(url: str, max_chars: int = 1800) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        with httpx.Client(timeout=6.0, follow_redirects=True, headers=HEADERS) as client:
            res = client.get(url)
            if res.status_code != 200 or "text/html" not in res.headers.get("content-type", ""):
                return ""
            soup = BeautifulSoup(res.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ", strip=True).split())
            return text[:max_chars]
    except Exception:
        return ""


class ResearchAgent:
    """محرك البحث الحي واستخلاص البيانات الحقيقية وتدقيق المراجع."""

    def search_web(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        if DDGS is None:
            return []
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, region="sa-ar", max_results=max_results))
                if not raw:
                    raw = list(ddgs.text(query, max_results=max_results))
                return [
                    {
                        "title": str(item.get("title", "")).strip(),
                        "href": str(item.get("href", "")).strip(),
                        "body": str(item.get("body", "")).strip(),
                    }
                    for item in raw if item.get("href")
                ]
        except Exception as exc:
            print(f"Search Err: {exc}", flush=True)
            return []

    def _enrich_sources(self, sources: list[dict[str, str]]) -> list[dict[str, str]]:
        top_urls = [s["href"] for s in sources[:3]]
        with ThreadPoolExecutor(max_workers=3) as pool:
            extracted = list(pool.map(_scrape_url, top_urls))
        for idx, content in enumerate(extracted):
            if len(content) > 150:
                sources[idx]["full_text"] = content
        return sources

    def deep_research(self, query: str, max_results: int = 5) -> str:
        sources = self.search_web(query, max_results=max_results)
        if not sources:
            return ai_ask(query, f"التاريخ اليوم: {_today_stamp()}. أجب بدقة وموضوعية باللغة العربية:", mode="arabic")

        enriched = self._enrich_sources(sources)
        evidence = "\n\n".join(
            f"[{i}] {s['title']}\nالرابط: {s['href']}\nالمقتطف: {s['body']}\n"
            + (f"المحتوى المستخرج من الصفحة: {s['full_text']}" if s.get("full_text") else "")
            for i, s in enumerate(enriched, 1)
        )
        sys_prompt = (
            f"أنت باحث استقصائي ومدقق حقائق. التاريخ الفعلي اليوم: {_today_stamp()}.\n"
            "استخلص الحقائق والأرقام المؤكدة من المصادر الحية المرفقة فقط، ووثّق كل معلومة برقم المرجع [1] أو [2] بأسلوب عربي احترافي موجز."
        )
        synthesis = ai_ask(f"موضوع البحث: {query}\n\nالمصادر الحية:\n{evidence}", sys_prompt, temperature=0.2, mode="arabic")
        citations = "\n".join(f"• [{i}] {s['title']} — {s['href']}" for i, s in enumerate(enriched, 1))
        return f"📚 *نتائج البحث الحي وتدقيق المراجع ({_today_stamp()}):*\n\n{synthesis}\n\n🔗 *المصادر الموثقة:*\n{citations}"

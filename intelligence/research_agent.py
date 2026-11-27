from concurrent.futures import ThreadPoolExecutor
import re
from typing import Any
import httpx
import pendulum
from bs4 import BeautifulSoup
from hijridate import Gregorian
from core.core_ai import ai_ask

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

try:
    import wikipediaapi
except ImportError:
    wikipediaapi = None

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import arxiv
except ImportError:
    arxiv = None

try:
    import trafilatura
except ImportError:
    trafilatura = None

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _today_stamp() -> str:
    now = pendulum.now("Asia/Riyadh")
    h = Gregorian(now.year, now.month, now.day).to_hijri()
    return f"{h.day}/{h.month}/{h.year}هـ ({now.format('YYYY-MM-DD')}م)"


def _scrape_url(url: str, max_chars: int = 2000) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        if trafilatura is not None:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                extracted = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
                if extracted and len(extracted.strip()) > 120:
                    return extracted.strip()[:max_chars]

        with httpx.Client(timeout=5.5, follow_redirects=True, headers=HEADERS) as client:
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
    """محرك المعرفة الشامل: يدمج الويب، الموسوعات، الأسواق المالية، والأبحاث العلمية بالتوازي."""

    def __init__(self) -> None:
        self.wiki_ar = wikipediaapi.Wikipedia(user_agent="AlbaraaAIOS/3.4", language="ar") if wikipediaapi else None
        self.wiki_en = wikipediaapi.Wikipedia(user_agent="AlbaraaAIOS/3.4", language="en") if wikipediaapi else None

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

    def _fetch_wikipedia(self, query: str) -> str:
        if not self.wiki_ar:
            return ""
        try:
            clean_q = re.sub(r"\b(?:ما هو|ما هي|من هو|من هي|تعريف|معلومات عن|نبذة عن|شرح)\b", "", query).strip()
            if len(clean_q) < 2:
                return ""
            page = self.wiki_ar.page(clean_q)
            if not page.exists() and self.wiki_en:
                page = self.wiki_en.page(clean_q)
            if page.exists() and page.summary:
                return f"📖 [موسوعة ويكيبيديا - {page.title}]:\n{page.summary[:1200]}"
        except Exception:
            pass
        return ""

    def _fetch_market_snapshot(self, query: str) -> str:
        if yf is None:
            return ""
        low = query.lower()
        tickers = {}
        if any(k in low for k in ("ذهب", "gold")):
            tickers["الذهب (Gold)"] = "GC=F"
        if any(k in low for k in ("نفط", "بترول", "oil", "برنت")):
            tickers["نفط برنت (Brent)"] = "BZ=F"
        if any(k in low for k in ("بيتكوين", "bitcoin", "btc", "عملات رقمية")):
            tickers["بيتكوين (BTC)"] = "BTC-USD"
        if any(k in low for k in ("أرامكو", "ارامكو", "aramco")):
            tickers["أرامكو السعودية (2222.SR)"] = "2222.SR"
        if any(k in low for k in ("الراجحي", "alrajhi")):
            tickers["مصرف الراجحي (1120.SR)"] = "1120.SR"
        if any(k in low for k in ("تاسي", "تداول", "tasi")):
            tickers["مؤشر تاسي (TASI)"] = "^TASI.SR"
        if any(k in low for k in ("دولار", "ريال", "usd", "sar")):
            tickers["الدولار مقابل الريال"] = "SAR=X"

        if not tickers:
            return ""
        lines = []
        for label, sym in list(tickers.items())[:3]:
            try:
                hist = yf.Ticker(sym).history(period="1d")
                if not hist.empty:
                    price = round(float(hist["Close"].iloc[-1]), 2)
                    lines.append(f"• {label}: {price}")
            except Exception:
                continue
        return "📈 [بيانات الأسواق الحية]:\n" + "\n".join(lines) if lines else ""

    def _fetch_arxiv(self, query: str) -> str:
        if arxiv is None:
            return ""
        if not any(k in query.lower() for k in ("بحث علمي", "دراسة", "ورقة علمية", "ذكاء اصطناعي", "خوارزمية", "paper", "arxiv", "research")):
            return ""
        try:
            en_q = ai_ask(query, "2 English scientific keywords only:", mode="fast").strip()
            search = arxiv.Search(query=en_q, max_results=2, sort_by=arxiv.SortCriterion.Relevance)
            papers = [f"• {r.title} ({r.published.year}): {r.summary[:350]}..." for r in search.results()]
            return "🔬 [أحدث الأوراق العلمية - ArXiv]:\n" + "\n".join(papers) if papers else ""
        except Exception:
            return ""

    def _enrich_sources(self, sources: list[dict[str, str]]) -> list[dict[str, str]]:
        top_urls = [s["href"] for s in sources[:3]]
        with ThreadPoolExecutor(max_workers=3) as pool:
            extracted = list(pool.map(_scrape_url, top_urls))
        for idx, content in enumerate(extracted):
            if len(content) > 150:
                sources[idx]["full_text"] = content
        return sources

    def deep_research(self, query: str, max_results: int = 5) -> str:
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_web = executor.submit(self.search_web, query, max_results)
            f_wiki = executor.submit(self._fetch_wikipedia, query)
            f_mkt = executor.submit(self._fetch_market_snapshot, query)
            f_sci = executor.submit(self._fetch_arxiv, query)

            sources = f_web.result()
            wiki_ctx = f_wiki.result()
            mkt_ctx = f_mkt.result()
            sci_ctx = f_sci.result()

        extra_blocks = [b for b in (mkt_ctx, wiki_ctx, sci_ctx) if b]

        if not sources and not extra_blocks:
            return ai_ask(query, f"التاريخ اليوم: {_today_stamp()}. أجب بدقة وموضوعية باللغة العربية:", mode="arabic")

        enriched = self._enrich_sources(sources) if sources else []
        web_evidence = "\n\n".join(
            f"[{i}] {s['title']}\nالرابط: {s['href']}\nالمقتطف: {s['body']}\n"
            + (f"المحتوى المستخرج: {s['full_text']}" if s.get("full_text") else "")
            for i, s in enumerate(enriched, 1)
        )

        full_evidence = "\n\n".join(extra_blocks + ([web_evidence] if web_evidence else []))
        sys_prompt = (
            f"أنت باحث استقصائي ومدقق حقائق. التاريخ الفعلي اليوم: {_today_stamp()}.\n"
            "استخلص الحقائق والأرقام المؤكدة من المصادر الحية المرفقة فقط، ووثّق كل معلومة برقم المرجع [1] أو [2] بأسلوب عربي احترافي موجز."
        )
        synthesis = ai_ask(f"موضوع البحث: {query}\n\nالمصادر الحية المجمعة:\n{full_evidence}", sys_prompt, temperature=0.2, mode="arabic")
        citations = "\n".join(f"• [{i}] {s['title']} — {s['href']}" for i, s in enumerate(enriched, 1))
        footer = f"\n\n🔗 *المصادر الموثقة:*\n{citations}" if citations else ""
        return f"📚 *نتائج البحث الحي وتدقيق المراجع ({_today_stamp()}):*\n\n{synthesis}{footer}"

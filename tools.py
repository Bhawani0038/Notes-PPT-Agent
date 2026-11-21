"""Free research tools: DuckDuckGo search, Wikipedia, page text extraction."""
import requests

HEADERS = {"User-Agent": "ContentAgents/1.0 (educational use)"}


def web_search(query, n=5):
    try:
        from ddgs import DDGS
        res = DDGS().text(query, max_results=n)
        return [{"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")} for r in res]
    except Exception:
        return []


def wikipedia(query, n=2):
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "generator": "search", "gsrsearch": query, "gsrlimit": n,
                    "prop": "extracts", "explaintext": 1, "exlimit": n, "exchars": 3000, "format": "json"},
            headers=HEADERS, timeout=20)
        pages = r.json().get("query", {}).get("pages", {}).values()
        return [{"title": p["title"], "url": "https://en.wikipedia.org/wiki/" + p["title"].replace(" ", "_"),
                 "snippet": p.get("extract", "")} for p in pages]
    except Exception:
        return []


def page_text(url, limit=1800):
    try:
        import trafilatura
        html = trafilatura.fetch_url(url)
        text = trafilatura.extract(html) if html else None
        return (text or "")[:limit]
    except Exception:
        return ""


def gather_sources(queries, max_chars=10000, fetch_pages=4):
    """Queries chalata hai, unique sources jodta hai, ek text block banata hai."""
    seen, blocks, total, n = set(), [], 0, 0
    for q in queries:
        items = web_search(q, 4) + wikipedia(q, 1)
        for it in items:
            if not it["url"] or it["url"] in seen:
                continue
            seen.add(it["url"])
            body = it["snippet"]
            if n < fetch_pages and "wikipedia.org" not in it["url"]:
                body = (page_text(it["url"]) or body)
            n += 1
            block = f"[{n}] {it['title']}\nURL: {it['url']}\n{body[:1800]}\n"
            if total + len(block) > max_chars:
                return "\n".join(blocks)
            blocks.append(block)
            total += len(block)
    return "\n".join(blocks)

"""OpenAlex API(무료, 키 불필요)로 arXiv에 없는 저널/학회 논문까지 확장 수집."""
import urllib.parse
import urllib.request
import json
from datetime import date, timedelta
import config


def _reconstruct_abstract(inverted_index) -> str:
    """OpenAlex는 초록을 {단어: [위치, ...]} 형태로 주기 때문에 원문 순서로 재조립."""
    if not inverted_index:
        return ""
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def fetch_papers(query: str) -> list:
    today = date.today()
    since = today - timedelta(days=config.PAPER_MAX_AGE_DAYS)
    params = {
        "search": query,
        "sort": "publication_date:desc",
        "per-page": 10,
        "filter": (
            f"from_publication_date:{since.isoformat()},"
            f"to_publication_date:{today.isoformat()},"
            "type:article|preprint"
        ),
    }
    url = f"https://api.openalex.org/works?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-news-bot (mailto:example@example.com)"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception:
        return []

    papers = []
    for w in data.get("results", []):
        link = (w.get("primary_location") or {}).get("landing_page_url") or w.get("id") or ""
        title = (w.get("title") or "").strip()
        if not link or not title:
            continue
        authors = ", ".join(
            a["author"]["display_name"]
            for a in w.get("authorships", [])[:3]
            if a.get("author")
        )
        papers.append({
            "title": title,
            "summary": _reconstruct_abstract(w.get("abstract_inverted_index"))[:500],
            "link": link,
            "authors": authors,
        })
    return papers

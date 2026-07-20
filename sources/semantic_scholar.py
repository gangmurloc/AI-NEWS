"""Semantic Scholar API(무료, 키 불필요)로 논문 추가 수집.
키 없는 공용 요청은 전 세계 사용자와 요청 한도를 공유해서 자주 429로 실패한다.
그래서 실패하면 예외를 던지지 않고 조용히 빈 목록을 반환 — 되면 보너스, 안 되면 arXiv/OpenAlex만 사용."""
import urllib.parse
import urllib.request
import json
from datetime import date, timedelta
import config

API = "https://api.semanticscholar.org/graph/v1/paper/search"


def fetch_papers(query: str) -> list:
    params = {
        "query": query,
        "fields": "title,abstract,url,authors,publicationDate",
        "limit": 10,
        "sort": "publicationDate:desc",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-news-bot"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception:
        return []

    cutoff = (date.today() - timedelta(days=config.PAPER_MAX_AGE_DAYS)).isoformat()

    papers = []
    for p in data.get("data") or []:
        pub_date = p.get("publicationDate")
        if not pub_date or pub_date < cutoff:
            continue
        link = p.get("url") or ""
        title = (p.get("title") or "").strip()
        if not link or not title:
            continue
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3])
        papers.append({
            "title": title,
            "summary": (p.get("abstract") or "")[:500],
            "link": link,
            "authors": authors,
        })
    return papers

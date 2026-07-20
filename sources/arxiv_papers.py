"""arXiv 공개 API로 최신 논문 수집 (API 키 불필요)."""
import urllib.parse
import feedparser
import config

ARXIV_API = "http://export.arxiv.org/api/query"


def fetch_recent_papers():
    cat_query = " OR ".join(f"cat:{c}" for c in config.ARXIV_CATEGORIES)
    keyword_query = " OR ".join(f'abs:"{k}"' for k in config.ARXIV_KEYWORDS)
    search_query = f"({cat_query}) AND ({keyword_query})"
    params = {
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": config.ARXIV_MAX_RESULTS,
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    feed = feedparser.parse(url)

    papers = []
    for entry in feed.entries:
        papers.append({
            "title": entry.title.strip().replace("\n", " "),
            "summary": entry.summary.strip().replace("\n", " ")[:500],
            "link": entry.link,
            "authors": ", ".join(a.name for a in entry.authors[:3]),
        })
    return papers

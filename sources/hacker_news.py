"""Hacker News(Algolia 검색 API, 무료/키 불필요)에서 커뮤니티가 이미 투표한 글을 수집.
포인트(추천수) 기준으로 걸러서 품질 신호로 사용."""
import time
import urllib.parse
import urllib.request
import json
import config

HN_API = "https://hn.algolia.com/api/v1/search"


def fetch_hn_stories(query: str) -> list:
    cutoff = int(time.time()) - config.HN_MAX_AGE_DAYS * 86400
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{cutoff},points>={config.HN_MIN_POINTS}",
        "hitsPerPage": config.HN_MAX_RESULTS,
    }
    url = f"{HN_API}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ai-news-bot"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception:
        return []  # HN이 안 되도 전체 파이프라인은 계속 진행

    articles = []
    for hit in data.get("hits", []):
        title = hit.get("title")
        object_id = hit.get("objectID")
        if not title or not object_id:
            continue  # 필수 필드가 빠진 항목 하나 때문에 전체 HN 수집이 죽지 않도록 건너뜀
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
        articles.append({
            "title": title,
            "link": link,
            "source": f"Hacker News ({hit.get('points', 0)}점, 댓글 {hit.get('num_comments', 0)}개)",
            "published": hit.get("created_at", ""),
            "published_ts": hit.get("created_at_i", 0),
        })
    return articles

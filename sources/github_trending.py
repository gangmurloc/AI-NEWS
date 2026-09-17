"""GitHub Search API(무료, 키 불필요)로 최근 생성되고 스타가 많은 AI 관련 레포를 수집.
GitHub는 '진짜 트렌딩'(스타 증가 속도) 공식 API가 없어서, 최근 N일 내 생성 + 스타 많은 순으로 근사한다."""
import urllib.parse
import urllib.request
import json
from datetime import timedelta
import config
import history

API = "https://api.github.com/search/repositories"


def fetch_trending_repos() -> list:
    since = (config.today_kst() - timedelta(days=config.GITHUB_TRENDING_MAX_AGE_DAYS)).isoformat()

    repos = {}
    for keyword in config.GITHUB_TRENDING_KEYWORDS:
        params = {
            "q": f"{keyword} in:name,description,topics created:>{since}",
            "sort": "stars",
            "order": "desc",
            "per_page": config.GITHUB_TRENDING_MAX_RESULTS,
        }
        url = f"{API}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "ai-news-bot",
            "Accept": "application/vnd.github+json",
        })
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        except Exception:
            continue  # 검색 API는 비인증 요청 한도가 낮아 실패해도 전체 파이프라인은 계속 진행

        for item in data.get("items", []):
            full_name = item.get("full_name")
            if not full_name or full_name in repos:
                continue
            repos[full_name] = {
                "title": full_name,
                "link": item.get("html_url", ""),
                "stars": item.get("stargazers_count", 0),
                "description": (item.get("description") or "").strip()[:200],
            }

    ranked = sorted(repos.values(), key=lambda r: r["stars"], reverse=True)
    ranked = history.filter_unsent(ranked)
    return ranked[: config.GITHUB_TRENDING_MAX_RESULTS]


def format_trending(repos: list) -> str:
    if not repos:
        return "오늘은 새로 떠오르는 레포를 찾지 못했습니다."

    lines = []
    for i, r in enumerate(repos, 1):
        desc = f"\n   {r['description']}" if r["description"] else ""
        lines.append(f"{i}) {r['title']} (⭐{r['stars']}){desc}\n   {r['link']}")
    return "\n\n".join(lines)

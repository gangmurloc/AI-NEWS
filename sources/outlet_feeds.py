"""신뢰도 높은 매체의 공식 AI 카테고리 RSS(무료, 키 불필요)를 모아서 공통 후보군으로 사용."""
import calendar
import time
import feedparser
import config

# Reddit은 봇 티가 나는 User-Agent(예: "xxx-bot/1.0")는 429로 차단하고, 브라우저처럼 보이는
# User-Agent에는 정상 응답한다. 다른 매체 RSS에도 문제없이 쓸 수 있어 전체에 공용으로 사용.
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_outlet_articles() -> list:
    cutoff_ts = time.time() - config.OUTLET_MAX_AGE_DAYS * 86400

    articles = []
    for name, url in config.TRUSTED_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": _USER_AGENT})
        except Exception:
            continue
        for entry in feed.entries:
            try:
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if not published_parsed:
                    continue
                published_ts = calendar.timegm(published_parsed)
                if published_ts < cutoff_ts:
                    continue
                articles.append({
                    "title": entry.title.strip(),
                    "link": entry.link,
                    "source": name,
                    "published": entry.get("published", entry.get("updated", "")),
                    "published_ts": published_ts,
                })
            except (AttributeError, TypeError):
                continue  # 항목 하나가 깨져도 같은 피드의 나머지, 다른 피드는 계속 수집
    return articles

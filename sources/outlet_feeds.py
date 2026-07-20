"""신뢰도 높은 매체의 공식 AI 카테고리 RSS(무료, 키 불필요)를 모아서 공통 후보군으로 사용."""
import calendar
import time
import feedparser
import config


def fetch_outlet_articles() -> list:
    cutoff_ts = time.time() - config.OUTLET_MAX_AGE_DAYS * 86400

    articles = []
    for name, url in config.TRUSTED_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
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

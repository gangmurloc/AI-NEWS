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
    return articles

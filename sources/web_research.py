"""Google News RSS(무료, 키 불필요)로 주제별 최신 뉴스를 수집하고 Gemini로 정리."""
import urllib.parse
import feedparser
from google import genai
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


def _fetch_rss(topic: str):
    query = urllib.parse.quote(topic)
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)

    articles = []
    for entry in feed.entries[: config.NEWS_MAX_RESULTS]:
        source = entry.source.title if hasattr(entry, "source") else ""
        articles.append({
            "title": entry.title.strip(),
            "link": entry.link,
            "source": source,
            "published": entry.get("published", ""),
        })
    return articles


def research_topic(topic: str) -> str:
    articles = _fetch_rss(topic)
    if not articles:
        return f"'{topic}' 관련 최신 뉴스를 찾지 못했습니다."

    raw = "\n".join(
        f"- 제목: {a['title']} | 출처: {a['source']} | 날짜: {a['published']} | 링크: {a['link']}"
        for a in articles
    )
    prompt = f"""아래는 '{topic}' 관련 오늘 수집된 뉴스 목록이야.

규칙:
- 중복되거나 비슷한 내용은 하나로 합쳐서 핵심만 3~5개 선별
- 각 항목은 [제목] + 2문장 요약 + 출처 링크 형식
- 한국어로 작성
- 목록에 없는 내용은 지어내지 말 것

뉴스 목록:
{raw}"""
    try:
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
        )
        return resp.text
    except Exception as e:
        return f"({topic} 정리 실패: {e})\n\n원본 목록:\n{raw}"

"""Google News RSS(무료, 키 불필요)로 주제별 최신 해외 뉴스를 수집하고 Gemini로 정리."""
import urllib.parse
import feedparser
import config
from gemini_client import generate, TELEGRAM_FORMAT_RULES


def _fetch_rss(query: str):
    # when:Nd 연산자로 최근 N일 이내 기사만 검색 (Google News 검색 문법)
    full_query = f"{query} when:{config.NEWS_MAX_AGE_DAYS}d"
    params = {"q": full_query, **config.NEWS_LANG}
    url = f"https://news.google.com/rss/search?{urllib.parse.urlencode(params)}"
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


def research_topic(query: str, label: str) -> str:
    articles = _fetch_rss(query)
    if not articles:
        return f"'{label}' 관련 최근 {config.NEWS_MAX_AGE_DAYS}일 이내 뉴스를 찾지 못했습니다."

    raw = "\n".join(
        f"- 제목: {a['title']} | 출처: {a['source']} | 날짜: {a['published']} | 링크: {a['link']}"
        for a in articles
    )
    prompt = f"""아래는 '{label}' 관련 해외(영어) 매체에서 수집된 최근 {config.NEWS_MAX_AGE_DAYS}일 이내 뉴스 목록이야.

규칙:
- 포함: 주요 매체(TechCrunch, The Verge, Ars Technica, Reuters, Bloomberg, MIT Technology
  Review, Wired, VentureBeat 등)의 보도, 회사 공식 발표/블로그, MarkTechPost 같은 AI 전문
  매체의 실질적인 뉴스(신제품/모델 출시, 연구 결과, 기술 분석 등)
- 제외: 가격비교·배팅(odds & predictions)·제휴링크성 클릭베이트, "OO가지 트렌드" 식 범용
  목록형 콘텐츠, 주가/시황 분석, 출처 불명확한 저품질 기사
- 위 조건을 만족하는 기사가 3개 미만이면 억지로 채우지 말고 있는 만큼만 선별
- 중복되거나 비슷한 내용은 하나로 합쳐서 핵심만 최대 5개 선별
- 각 항목은 제목(한국어로 번역) + 2문장 한국어 요약 + 출처 링크 형식
- 전체 한국어로 작성
- 목록에 없는 내용은 지어내지 말 것

{TELEGRAM_FORMAT_RULES}

뉴스 목록:
{raw}"""
    try:
        return generate(prompt)
    except Exception as e:
        return f"({label} 정리 실패: {e})\n\n원본 목록:\n{raw}"

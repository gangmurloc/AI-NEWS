"""Google News + Hacker News + 신뢰 매체 RSS(전부 무료, 키 불필요)로 뉴스를 모아 LLM으로 정리."""
import calendar
import time
import urllib.parse
import feedparser
import config
import history
from sources.hacker_news import fetch_hn_stories
from llm_client import generate, TELEGRAM_FORMAT_RULES


def _fetch_google_news(query: str) -> list:
    # when:Nd 연산자로 최근 N일 이내 기사만 검색 (Google News 검색 문법)
    full_query = f"{query} when:{config.NEWS_MAX_AGE_DAYS}d"
    params = {"q": full_query, **config.NEWS_LANG}
    url = f"https://news.google.com/rss/search?{urllib.parse.urlencode(params)}"
    feed = feedparser.parse(url)

    articles = []
    for entry in feed.entries:
        try:
            source = entry.source.title if hasattr(entry, "source") else ""
            published_parsed = entry.get("published_parsed") or time.gmtime(0)
            articles.append({
                "title": entry.title.strip(),
                "link": entry.link,
                "source": source,
                "published": entry.get("published", ""),
                "published_ts": calendar.timegm(published_parsed),
            })
        except (AttributeError, TypeError):
            continue  # 항목 하나가 깨져도 나머지는 계속 수집
    return articles


def fetch_topic_articles(query: str, hn_query: str, outlet_articles: list, exclude_links: set = frozenset()) -> list:
    """Google News + Hacker News + 신뢰 매체 RSS를 합쳐서 최신순 정렬 → 이미 보낸 링크/앞선 토픽에서 쓴 링크 제외 → 상위 N개.

    exclude_links: 같은 브리핑 안에서 앞선 토픽이 이미 채택한 링크 (여러 토픽에 같은 기사가 중복 등장하는 것을 방지)"""
    articles = _fetch_google_news(query) + fetch_hn_stories(hn_query) + outlet_articles
    articles.sort(key=lambda a: a["published_ts"], reverse=True)
    articles = history.filter_unsent(articles)
    articles = [a for a in articles if a["link"] not in exclude_links]
    return articles[: config.NEWS_MAX_RESULTS + config.HN_MAX_RESULTS]


def summarize_core_news(articles: list) -> str:
    if not articles:
        return "새로 전할 만한 핵심 AI 뉴스가 없습니다."

    raw = "\n".join(
        f"- 제목: {a['title']} | 출처: {a['source']} | 날짜: {a['published']} | 링크: {a['link']}"
        for a in articles
    )
    prompt = f"""아래는 여러 AI 관심 주제에서 모은 뉴스 후보 목록이야. Google News, Hacker News(개발자 커뮤니티가 이미 추천/토론한 글,
"Hacker News (N점, 댓글 N개)"로 표시됨), TechCrunch/VentureBeat/The Verge/Lobsters 같은 신뢰 매체의
AI 카테고리 기사를 모두 합친 결과라서 관련 없는 기사도 섞여 있을 수 있어.

규칙:
- AI 업계나 실제 개발 업무에 영향이 큰 기사만 골라낼 것. 관련 없는 기사는 무시
- 그 중에서도 실질적인 뉴스(신제품/모델 출시, 연구 결과, 기술 분석 등)와 포인트가 높은
  Hacker News 글을 우선 선별
- 제외: 가격비교·배팅(odds & predictions)·제휴링크성 클릭베이트, "OO가지 트렌드" 식 범용
  목록형 콘텐츠, 주가/시황 분석, 출처 불명확한 저품질 기사
- 조건을 만족하는 기사가 적으면 억지로 채우지 말고 있는 만큼만 선별
- 중복되거나 비슷한 내용은 하나로 합쳐서 핵심만 최대 {config.CORE_NEWS_MAX_ITEMS}개 선별
- 각 항목은 제목(한국어로 번역) + 왜 중요한지 포함한 2문장 한국어 요약 + 출처 링크 형식
- 전체 한국어로 작성
- 목록에 없는 내용은 지어내지 말 것

{TELEGRAM_FORMAT_RULES}

뉴스 후보 목록:
{raw}"""
    try:
        return generate(prompt)
    except Exception as e:
        title_links = "\n".join(
            f"- {a['title']} ({a['link']})"
            for a in articles[: config.CORE_NEWS_MAX_ITEMS]
        )
        return f"(핵심 뉴스 정리 실패: {type(e).__name__})\n\n{title_links}"


def summarize_topic(articles: list, label: str) -> str:
    """이전 호출부와의 호환성을 유지한다."""
    return summarize_core_news(articles)

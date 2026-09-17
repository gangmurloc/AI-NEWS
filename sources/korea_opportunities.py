"""국내 AI 대회·공모전·해커톤·교육/지원사업 후보를 수집하고 구조화한다."""
import calendar
from concurrent.futures import ThreadPoolExecutor
import html
import re
import time
import urllib.parse

import feedparser
import requests
from bs4 import BeautifulSoup

import config
import history
from llm_client import TELEGRAM_FORMAT_RULES, generate


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_SPACE_RE = re.compile(r"\s+")
_TITLE_SUFFIX_RE = re.compile(r"\s+[-|]\s+[^-|]{1,40}$")
_AI_RE = re.compile(r"\bAI\b|인공지능|데이터|로봇|\bSW\b", re.IGNORECASE)
_OPPORTUNITY_RE = re.compile(
    r"대회|공모|경진|해커톤|교육생|참가자|모집|접수|지원사업|창업지원"
)


def _unwrap_bing_link(link: str) -> str:
    """Bing RSS 추적 URL에서 실제 기사 URL을 꺼낸다."""
    parsed = urllib.parse.urlparse(link)
    if parsed.netloc.endswith("bing.com"):
        target = urllib.parse.parse_qs(parsed.query).get("url", [""])[0]
        if target:
            return urllib.parse.unquote(target)
    return link


def _plain_text(value: str) -> str:
    soup = BeautifulSoup(html.unescape(value or ""), "html.parser")
    return _SPACE_RE.sub(" ", soup.get_text(" ", strip=True)).strip()


def _fetch_search_results(topic: dict) -> list[dict]:
    cutoff_ts = time.time() - config.OPPORTUNITY_MAX_AGE_DAYS * 86400
    results = []
    queries = topic.get("queries") or [topic.get("query", "")]
    for query in filter(None, queries):
        params = {"q": query, "format": "rss", "setlang": "ko-KR"}
        url = f"https://www.bing.com/news/search?{urllib.parse.urlencode(params)}"
        feed = feedparser.parse(url, request_headers={"User-Agent": _USER_AGENT})
        for entry in feed.entries[: config.OPPORTUNITY_MAX_RESULTS_PER_TOPIC]:
            published_parsed = entry.get("published_parsed")
            published_ts = calendar.timegm(published_parsed) if published_parsed else 0
            if published_ts and published_ts < cutoff_ts:
                continue

            link = _unwrap_bing_link(entry.get("link", ""))
            title = _plain_text(entry.get("title", ""))
            if not title or not link:
                continue
            snippet = _plain_text(entry.get("summary", entry.get("description", "")))
            search_text = f"{title} {snippet}"
            if not _AI_RE.search(search_text) or not _OPPORTUNITY_RE.search(search_text):
                continue

            source = ""
            source_info = entry.get("source")
            if isinstance(source_info, dict):
                source = source_info.get("title", "")
            source = source or entry.get("news_source", "")
            results.append({
                "title": title,
                "link": link,
                "source": _plain_text(source),
                "published": entry.get("published", ""),
                "published_ts": published_ts,
                "snippet": snippet,
                "request_label": topic["label"],
            })
    return results


def _extract_page_details(url: str) -> tuple[str, list[str]]:
    """원문 본문과 신청 가능성이 높은 링크를 추출한다."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"},
            timeout=config.OPPORTUNITY_PAGE_TIMEOUT,
        )
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", "").lower():
            return "", []
    except requests.RequestException:
        return "", []

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()

    application_links = []
    link_words = re.compile(r"신청|접수|참가|지원|공고|홈페이지|대회|공모")
    for anchor in soup.select("a[href]"):
        label = _SPACE_RE.sub(" ", anchor.get_text(" ", strip=True))
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        if link_words.search(label):
            absolute_url = urllib.parse.urljoin(response.url, href)
            if absolute_url.startswith(("http://", "https://")) and absolute_url not in application_links:
                application_links.append(absolute_url)

    selectors = [
        "[itemprop='articleBody']",
        ".article-body",
        ".article_view",
        ".view-content",
        ".board-view",
        ".board_view",
        "article",
        "main",
        "#content",
    ]
    candidates = []
    for selector in selectors:
        for node in soup.select(selector):
            text = _SPACE_RE.sub(" ", node.get_text(" ", strip=True)).strip()
            if len(text) >= 120:
                candidates.append(text)

    if not candidates:
        candidates = [_SPACE_RE.sub(" ", soup.get_text(" ", strip=True)).strip()]
    body = max(candidates, key=len, default="")
    return body[: config.OPPORTUNITY_BODY_MAX_CHARS], application_links[:8]


def discover_opportunities(exclude_links: set[str] = frozenset()) -> list[dict]:
    """설정된 요청 주제를 검색하고 중복/기전송 항목을 제거한다."""
    candidates = []
    for topic in config.REQUESTED_INFO_TOPICS:
        candidates.extend(_fetch_search_results(topic))

    candidates.sort(key=lambda item: item.get("published_ts", 0), reverse=True)
    deduped = []
    seen_links = set()
    seen_titles = set()
    for item in candidates:
        title_key = _TITLE_SUFFIX_RE.sub("", item["title"]).lower().strip()
        link_key = item["link"].split("#", 1)[0]
        if link_key in seen_links or title_key in seen_titles:
            continue
        seen_links.add(link_key)
        seen_titles.add(title_key)
        deduped.append(item)

    unsent = history.filter_unsent(deduped)
    unsent = [item for item in unsent if item["link"] not in exclude_links]
    return unsent


def enrich_opportunities(items: list[dict]) -> list[dict]:
    """선별된 기회정보 후보에 원문과 신청 링크를 병렬로 보강한다."""

    def enrich(item: dict) -> dict:
        body, application_links = _extract_page_details(item["link"])
        item["body"] = body
        item["application_links"] = application_links
        return item

    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(6, len(items))) as executor:
        return list(executor.map(enrich, items))


def fetch_opportunities(exclude_links: set[str] = frozenset()) -> list[dict]:
    """기회정보 후보 중 요약할 상위 항목의 원문을 보강해 반환한다."""
    candidates = discover_opportunities(exclude_links)
    return enrich_opportunities(candidates[: config.OPPORTUNITY_MAX_CANDIDATES])


def summarize_opportunities(items: list[dict]) -> str:
    if not items:
        return "현재 새로 확인된 국내 AI 대회·공모전·모집 정보가 없습니다."

    raw_items = []
    for item in items:
        body = item.get("body") or item.get("snippet") or "원문 본문 확인 불가"
        raw_items.append(
            "\n".join([
                f"분류: {item['request_label']}",
                f"제목: {item['title']}",
                f"출처: {item['source']}",
                f"게시일: {item['published']}",
                f"본문: {body}",
                f"본문 내 신청 링크 후보: {', '.join(item.get('application_links', [])) or '없음'}",
                f"링크: {item['link']}",
            ])
        )

    today = config.today_kst().isoformat()
    prompt = f"""아래는 한국의 AI 관련 대회, 공모전, 경진대회, 해커톤, 교육 및 지원사업 후보야.
오늘 날짜는 {today}야. 실제로 국내에서 참여할 가치가 있는 모집 정보만 골라 한국어로 정리해줘.

선별 규칙:
- 접수 중이거나 접수 예정인 정보를 우선하고, 명백히 마감된 항목은 제외
- 기관 내부 직원만 참가하는 행사, 수상 결과 발표, 개최 후기는 제외
- 단순 뉴스나 제품 홍보처럼 참가 신청을 할 수 없는 글은 제외
- 같은 행사를 다룬 글은 하나만 남기고, 제공된 본문 내 신청 링크 후보가 적절하면 그 링크를 우선
- 후보 목록에 제공되지 않은 URL을 새로 만들거나 추측하지 말 것
- 원문에 없는 날짜, 참가 조건, 상금, 장소는 추측하지 말고 "확인 필요"라고 표시
- 최대 {config.OPPORTUNITY_FINAL_MAX_ITEMS}개만 선정하고, 조건에 맞는 항목이 적으면 억지로 채우지 말 것

출력 형식:
1) 행사명
- 상태: 접수 중 / 접수 예정 / 일정 확인 필요
- 접수 기간: YYYY-MM-DD ~ YYYY-MM-DD 또는 확인 필요
- 참가 대상: 원문에 적힌 대상 또는 확인 필요
- 주요 내용: 대회 주제와 혜택을 1~2문장
- 상금·혜택: 원문 내용 또는 확인 필요
- 장소·방식: 온라인/오프라인 장소 또는 확인 필요
- 신청 링크: URL

{TELEGRAM_FORMAT_RULES}

후보 목록:
{chr(10).join(raw_items)}"""
    try:
        return generate(prompt)
    except Exception as error:
        fallback = "\n".join(
            f"- {item['title']}\n  {item['link']}"
            for item in items[: config.OPPORTUNITY_FINAL_MAX_ITEMS]
        )
        return f"(기회정보 정리 실패: {type(error).__name__})\n\n{fallback}"

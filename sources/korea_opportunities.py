"""국내 AI 대회·공모전·해커톤·교육/지원사업 후보를 수집하고 구조화한다."""
import calendar
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import hashlib
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
_DEADLINE_CONTEXT_RE = re.compile(r"접수|신청|모집|마감|제출|등록")
_DATE_RE = re.compile(
    r"(?:(20\d{2})\s*(?:년|[./-])\s*)?"
    r"(\d{1,2})\s*(?:월|[./-])\s*(\d{1,2})\s*일?"
)
_STRONG_LINK_RE = re.compile(
    r"신청\s*하기|접수\s*하기|참가\s*신청|온라인\s*접수|지원\s*하기|바로\s*가기"
)
_GENERAL_LINK_RE = re.compile(r"신청|접수|참가|지원|공고|홈페이지|대회|공모")
_NATIONWIDE_ELIGIBILITY_RE = re.compile(
    r"전국\s*(?:민|누구나|대상|대학생|청년|기업)|"
    r"전국에서\s*(?:참가|신청|지원)|"
    r"지역\s*제한\s*(?:없음|없|없이)|거주지\s*제한\s*(?:없음|없|없이)"
)
_OUTSIDE_CAPITAL_REGION_RE = re.compile(
    r"부산(?:광역시)?|대구(?:광역시)?|인천(?:광역시)?|광주광역시|광주(?!시)|"
    r"대전(?:광역시)?|울산(?:광역시)?|세종(?:특별자치시)?|"
    r"강원(?:특별자치도|도)?|충청북도|충북|충청남도|충남|"
    r"전북(?:특별자치도)?|전라북도|전남|전라남도|"
    r"경북|경상북도|경남|경상남도|제주(?:특별자치도|도)?"
)
_LOCAL_ELIGIBILITY_RE = re.compile(
    r"거주|주민|시민|도민|군민|구민|지역민|소재|재학|재직|근무|"
    r"사업장|본사|주소지|관내|지역\s*내|지역\s*소재|지역\s*거주|"
    r"지역\s*(?:청년|학생|대학생|기업|창업자)"
)
_LOCALITY_ELIGIBILITY_RE = re.compile(
    r"(?P<locality>[가-힣]{2,7}(?:시|군|구))\s*"
    r"(?:민|주민|거주|소재|재학|재직|근무|사업장|본사|주소지)"
)
_REGION_GROUP_RE = re.compile(
    r"^\s*(?:지역\s*)?(?:청년|학생|대학생|기업|창업기업|창업자|예비창업자)"
    r"\s*(?:만|대상|한정)"
)
_SEOUL_GYEONGGI_LOCALITIES = {
    "서울시", "서울특별시", "경기도",
    "수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시",
    "동두천시", "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시",
    "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시", "이천시",
    "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시",
    "연천군", "가평군", "양평군",
    "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
    "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구",
    "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구",
    "서초구", "강남구", "송파구", "강동구",
}
_KNOWN_APPLICATION_HOSTS = {
    "dacon.io",
    "aihub.or.kr",
    "k-startup.go.kr",
    "onoffmix.com",
    "event-us.kr",
    "forms.gle",
    "docs.google.com",
    "naver.me",
}


def is_excluded_local_opportunity(title: str, body: str = "") -> bool:
    """서울·경기 밖 특정 지역 사람에게만 열린 기회정보인지 판별한다."""
    text = _SPACE_RE.sub(" ", f"{title or ''} {body or ''}").strip()
    if not text or _NATIONWIDE_ELIGIBILITY_RE.search(text):
        return False

    for region_match in _OUTSIDE_CAPITAL_REGION_RE.finditer(text):
        nearby = text[
            max(0, region_match.start() - 70): min(len(text), region_match.end() + 100)
        ]
        after_region = text[region_match.end(): min(len(text), region_match.end() + 45)]
        if _LOCAL_ELIGIBILITY_RE.search(nearby) or _REGION_GROUP_RE.search(after_region):
            return True

    for match in _LOCALITY_ELIGIBILITY_RE.finditer(text):
        if match.group("locality") not in _SEOUL_GYEONGGI_LOCALITIES:
            return True
    return False


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
            if is_excluded_local_opportunity(title, snippet):
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


def _rank_application_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    page_host = urllib.parse.urlparse(page_url).netloc.lower()
    ranked = []
    for order, anchor in enumerate(soup.select("a[href]")):
        label = _SPACE_RE.sub(" ", anchor.get_text(" ", strip=True))
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absolute_url = urllib.parse.urljoin(page_url, href)
        parsed = urllib.parse.urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue

        host = parsed.netloc.lower()
        score = 0
        if _STRONG_LINK_RE.search(label):
            score += 10
        elif _GENERAL_LINK_RE.search(label):
            score += 5
        if any(host == known or host.endswith(f".{known}") for known in _KNOWN_APPLICATION_HOSTS):
            score += 8
        if re.search(r"apply|application|register|contest|competition|event", parsed.path, re.IGNORECASE):
            score += 3
        if host and host != page_host:
            score += 2
        if score:
            ranked.append((score, -order, absolute_url))

    links = []
    for _, _, url in sorted(ranked, reverse=True):
        normalized = url.split("#", 1)[0]
        if normalized not in links:
            links.append(normalized)
    return links[:8]


def extract_page_details(url: str) -> tuple[str, list[str]]:
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

    application_links = _rank_application_links(soup, response.url)

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


def extract_deadline(text: str, today: date | None = None) -> str:
    """마감/접수기간 문맥이 명확한 날짜만 YYYY-MM-DD로 반환한다."""
    today = today or config.today_kst()
    contexts = []
    for match in _DEADLINE_CONTEXT_RE.finditer(text or ""):
        contexts.append(text[max(0, match.start() - 80): match.end() + 180])
    if not contexts:
        return ""

    parsed_dates = []
    for context in contexts:
        context_period = bool(re.search(r"(?:접수|신청|모집)\s*기간", context))
        for match in _DATE_RE.finditer(context):
            year = int(match.group(1) or today.year)
            month = int(match.group(2))
            day = int(match.group(3))
            try:
                value = date(year, month, day)
            except ValueError:
                continue
            if not match.group(1) and value < today - timedelta(days=180):
                value = date(year + 1, month, day)
            if not (today - timedelta(days=60) <= value <= today + timedelta(days=730)):
                continue

            nearby = context[max(0, match.start() - 45): match.end() + 45]
            score = 0
            if re.search(r"마감|까지", nearby):
                score += 10
            if context_period:
                score += 6
            before = context[max(0, match.start() - 35): match.start()]
            if re.search(r"접수|신청|모집", before):
                score += 2
            if re.search(r"~|∼|부터", before):
                score += 3
            if re.search(r"교육\s*기간|운영\s*기간|행사\s*기간|본선|결과\s*발표", nearby):
                score -= 8
            if score >= 4:
                parsed_dates.append((score, value))
    if not parsed_dates:
        return ""
    return max(parsed_dates, key=lambda candidate: (candidate[0], candidate[1]))[1].isoformat()


def build_preparation_checklist(text: str) -> list[str]:
    """원문에 실제로 나타난 제출물과 기본 확인 작업으로 체크리스트를 만든다."""
    text = text or ""
    checklist = ["공식 신청 페이지에서 최신 일정 확인", "참가 자격 및 팀 구성 조건 확인"]
    rules = [
        (r"참가신청서|신청서", "참가신청서 작성"),
        (r"개인정보.{0,12}동의", "개인정보 수집·이용 동의서 준비"),
        (r"사업계획서", "사업계획서 준비"),
        (r"제안서|기획서", "제안서·기획서 준비"),
        (r"발표자료|발표 자료|PPT", "발표자료 준비"),
        (r"소스\s*코드|깃허브|GitHub", "소스 코드 및 저장소 정리"),
        (r"시연\s*영상|소개\s*영상|동영상", "시연·소개 영상 준비"),
        (r"프로토타입|시제품", "프로토타입·시제품 준비"),
        (r"재학증명서|졸업증명서", "재학·졸업 증빙서류 준비"),
    ]
    for pattern, task in rules:
        if re.search(pattern, text, re.IGNORECASE) and task not in checklist:
            checklist.append(task)
    checklist.append("마감 전에 최종 제출 및 접수 완료 화면 보관")
    return checklist[:8]


def build_opportunity_record(item: dict) -> dict:
    body = item.get("body") or item.get("snippet") or ""
    normalized_body = _SPACE_RE.sub(" ", body).strip()
    application_links = item.get("application_links", [])
    return {
        "title": item.get("title", "").strip(),
        "source_link": item.get("link", ""),
        "application_link": application_links[0] if application_links else item.get("link", ""),
        "deadline": extract_deadline(normalized_body),
        "checklist": build_preparation_checklist(normalized_body),
        "content_hash": hashlib.sha256(normalized_body.encode("utf-8")).hexdigest(),
        "content_text": normalized_body,
    }


def discover_opportunities(
    exclude_links: set[str] = frozenset(), include_sent: bool = False
) -> list[dict]:
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

    unsent = deduped if include_sent else history.filter_unsent(deduped)
    unsent = [item for item in unsent if item["link"] not in exclude_links]
    return unsent


def enrich_opportunities(items: list[dict]) -> list[dict]:
    """선별된 기회정보 후보에 원문과 신청 링크를 병렬로 보강한다."""

    def enrich(item: dict) -> dict | None:
        body, application_links = extract_page_details(item["link"])
        if is_excluded_local_opportunity(item.get("title", ""), body or item.get("snippet", "")):
            return None
        item["body"] = body
        item["application_links"] = application_links
        item.update(build_opportunity_record(item))
        return item

    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(6, len(items))) as executor:
        return [item for item in executor.map(enrich, items) if item is not None]


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
                f"감지된 접수 마감일: {item.get('deadline') or '확인 필요'}",
                f"준비 체크리스트: {', '.join(item.get('checklist', []))}",
                f"링크: {item['link']}",
            ])
        )

    today = config.today_kst().isoformat()
    prompt = f"""아래는 한국의 AI 관련 대회, 공모전, 경진대회, 해커톤, 교육 및 지원사업 후보야.
오늘 날짜는 {today}야. 실제로 국내에서 참여할 가치가 있는 모집 정보만 골라 한국어로 정리해줘.

선별 규칙:
- 접수 중이거나 접수 예정인 정보를 우선하고, 명백히 마감된 항목은 제외
- 기관 내부 직원만 참가하는 행사, 수상 결과 발표, 개최 후기는 제외
- 서울·경기 이외 지역 거주자·재학생·소재 기업 등 해당 지역 사람만 참가할 수 있는 행사는 제외
- 지방에서 열리더라도 전국 누구나 참가할 수 있다고 명시된 행사는 제외하지 않음
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
- 준비 체크리스트: 원문에 근거한 준비 항목을 쉼표로 구분

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

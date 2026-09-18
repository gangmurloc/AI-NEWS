"""모든 설정을 한 곳에서 관리. 관심 주제는 자유롭게 수정하세요."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

KST = ZoneInfo("Asia/Seoul")


def today_kst():
    """GitHub Actions 러너는 UTC 시각이라 date.today()를 그대로 쓰면 한국시간 기준 날짜가 하루 밀림."""
    return datetime.now(KST).date()

# ----- .env 에서 불러오는 값 -----
# LLM은 OpenAI 호환 게이트웨이(factchat-cloud.mindlogic.ai)를 사용
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://factchat-cloud.mindlogic.ai/v1/gateway")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.6-luna")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

try:
    LIVE_POLL_INTERVAL_MINUTES = max(1, int(os.getenv("LIVE_POLL_INTERVAL_MINUTES", "1")))
except ValueError:
    LIVE_POLL_INTERVAL_MINUTES = 1
LIVE_POLL_INTERVAL_SECONDS = LIVE_POLL_INTERVAL_MINUTES * 60

# ----- 여기부터는 취향껏 수정 -----

# 매일 받아볼 관심 주제 (원하는 만큼 추가/삭제)
# label: 텔레그램에 표시될 한국어 제목
# query: Google News 검색에 쓰이는 영어 검색어 (길고 구체적이어도 됨)
# hn_query: Hacker News 검색에 쓰이는 짧은 키워드 (HN은 게시량이 적어서 너무 길면 결과가 0건이 됨)
TOPICS = [
    {
        "label": "LLM(대규모 언어모델) 최신 동향 및 신규 모델 출시",
        "query": "LLM new model release",
        "hn_query": "LLM",
    },
    {
        "label": "RAG(검색증강생성) 기술 및 프레임워크 소식",
        "query": "retrieval-augmented generation RAG",
        "hn_query": "RAG retrieval",
    },
    {
        "label": "AI 에이전트 및 에이전틱 워크플로우",
        "query": "AI agent agentic workflow",
        "hn_query": "AI agent",
    },
]

# 텔레그램에 최종 노출할 핵심 뉴스 수. TOPICS별로 따로 나열하지 않고 전체 후보에서 선별한다.
CORE_NEWS_MAX_ITEMS = 5
CORE_NEWS_MAX_CANDIDATES = 24

# 국내에서 참여할 수 있는 AI 대회/공모전/교육/지원사업 검색 목록.
# 앞으로 추가로 받고 싶은 정보가 생기면 같은 형식으로 항목만 덧붙이면 된다.
REQUESTED_INFO_TOPICS = [
    {
        "label": "국내 AI 대회·공모전·경진대회",
        "queries": [
            "AI 공모전 모집",
            "인공지능 경진대회 참가 모집",
            "데이터 분석 대회 참가 모집",
        ],
    },
    {
        "label": "국내 AI 해커톤",
        "queries": ["AI 해커톤 참가자 모집", "인공지능 해커톤 접수"],
    },
    {
        "label": "국내 AI 교육·지원사업",
        "queries": ["AI 교육생 모집", "인공지능 지원사업 모집"],
    },
]

# 기회정보는 뉴스보다 모집기간이 길어 최근 검색 범위를 넉넉하게 잡는다.
OPPORTUNITY_MAX_AGE_DAYS = 45
OPPORTUNITY_MAX_RESULTS_PER_TOPIC = 12
OPPORTUNITY_MAX_CANDIDATES = 20
OPPORTUNITY_FINAL_MAX_ITEMS = 8
OPPORTUNITY_PAGE_TIMEOUT = 12
OPPORTUNITY_BODY_MAX_CHARS = 3000
OPPORTUNITY_REFRESH_MINUTES = 30
OPPORTUNITY_REFRESH_BATCH_SIZE = 5
OPPORTUNITY_REMINDER_DAYS = [7, 3, 1, 0]
# 변경 알림은 짧은 문구·날짜·링크 수정이 아니라 본문을 사실상 다시 쓴 경우에만 보낸다.
OPPORTUNITY_MAJOR_CHANGE_MAX_SIMILARITY = 0.55
OPPORTUNITY_MAJOR_CHANGE_MIN_CHARS = 180

# 뉴스를 영어(해외) 매체 위주로 검색 (한국 매체의 낮은 품질의 PR성 기사를 줄이기 위함)
NEWS_LANG = {"hl": "en-US", "gl": "US", "ceid": "US:en"}

# Google News RSS에서 가져올 항목 수 (주제별)
NEWS_MAX_RESULTS = 8

# 최근 며칠 이내 기사만 수집 (Google News의 when: 검색 연산자에 사용)
NEWS_MAX_AGE_DAYS = 2

# Hacker News(커뮤니티가 이미 투표/토론한 글이라 품질 신호로 사용)에서 가져올 항목 수
HN_MAX_RESULTS = 5

# HN은 게시량이 적어서 Google News보다 넉넉하게 기간을 잡음
HN_MAX_AGE_DAYS = 5

# 이 포인트(추천수) 이상인 글만 채택 (너무 낮으면 잡담/스팸성 글까지 들어옴)
HN_MIN_POINTS = 15

# 뉴스 주제와 무관하게 항상 확인하는 신뢰도 높은 매체의 AI 카테고리 RSS (무료, 키 불필요)
# 이 매체들의 기사 자체가 이미 품질 필터링을 거친 것이므로 모든 주제의 후보군에 공통으로 포함
# Reddit은 top/.rss?t=day로 "오늘의 인기글"만 가져와 커뮤니티 품질 신호로 사용 (HN과 같은 역할)
TRUSTED_RSS_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Lobsters (AI)": "https://lobste.rs/t/ai.rss",
    "Reddit r/LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
    "Reddit r/MachineLearning": "https://www.reddit.com/r/MachineLearning/top/.rss?t=day",
}

# 매체별 게시 빈도가 낮은 경우가 있어 Google News보다 조금 넉넉하게 기간을 잡음
OUTLET_MAX_AGE_DAYS = 3

# arXiv 논문 카테고리 (예: cs.AI, cs.LG, cs.CL, cs.CV, stat.ML)
# cs.CL = 자연어처리(LLM/RAG 관련 논문이 주로 여기 올라옴)
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]

# 초록(abstract)에 이 키워드 중 하나라도 포함된 논문만 선별 (LLM/RAG 관련성 확보)
ARXIV_KEYWORDS = [
    "large language model",
    "LLM",
    "retrieval-augmented",
    "RAG",
    "agent",
]
ARXIV_MAX_RESULTS = 10

# 최근 며칠 이내 제출/발표된 논문만 선별 (arXiv, OpenAlex, Semantic Scholar 공통 적용)
# arXiv는 주말에는 논문을 발표하지 않으므로 2일보다 넉넉하게 잡아야 월요일에 결과가 비지 않음
PAPER_MAX_AGE_DAYS = 4

# 여러 논문 소스를 합친 뒤 LLM에게 넘길 최대 후보 수 (최종 선별은 LLM이 품질 기준으로 함)
PAPER_MAX_TOTAL = 35

# 논문 후보 중 텔레그램에 최종 노출할 수
PAPER_FINAL_MAX_RESULTS = 5

# GitHub Search API로 "최근 생성 + 스타 많은" AI 관련 레포를 찾음 (진짜 트렌딩 계산 API는 없어서 근사치)
GITHUB_TRENDING_KEYWORDS = ["llm", "rag", "ai-agent"]
GITHUB_TRENDING_MAX_AGE_DAYS = 14
GITHUB_TRENDING_MAX_RESULTS = 3

# 남은 LLM 크레딧이 전체 할당량의 이 비율보다 낮아지면 워치독이 미리 경고
# (Gemini 키가 예고 없이 소진돼서 요약만 조용히 실패했던 상황이 다시 반복되지 않도록)
LLM_CREDIT_ALERT_RATIO = 0.1


def validate():
    """필수 키가 비어있으면 친절하게 알려주고 종료."""
    required = {
        "LLM_API_KEY": LLM_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    missing = [k for k, v in required.items() if not v or "붙여넣기" in v]
    if missing:
        raise SystemExit(
            "[설정 오류] .env 파일에 다음 값을 채워주세요: " + ", ".join(missing)
        )

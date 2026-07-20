"""모든 설정을 한 곳에서 관리. 관심 주제는 자유롭게 수정하세요."""
import os
from dotenv import load_dotenv

load_dotenv()

# ----- .env 에서 불러오는 값 -----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

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
TRUSTED_RSS_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Lobsters (AI)": "https://lobste.rs/t/ai.rss",
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

# 여러 논문 소스를 합친 뒤 Gemini에게 넘길 최대 후보 수 (최종 선별은 Gemini가 품질 기준으로 함)
PAPER_MAX_TOTAL = 25


def validate():
    """필수 키가 비어있으면 친절하게 알려주고 종료."""
    required = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    missing = [k for k, v in required.items() if not v or "붙여넣기" in v]
    if missing:
        raise SystemExit(
            "[설정 오류] .env 파일에 다음 값을 채워주세요: " + ", ".join(missing)
        )

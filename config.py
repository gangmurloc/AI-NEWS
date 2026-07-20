"""모든 설정을 한 곳에서 관리. 관심 주제는 자유롭게 수정하세요."""
import os
from dotenv import load_dotenv

load_dotenv()

# ----- .env 에서 불러오는 값 -----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ----- 여기부터는 취향껏 수정 -----

# 매일 받아볼 관심 주제 (원하는 만큼 추가/삭제)
TOPICS = [
    "LLM(대규모 언어모델) 최신 동향 및 신규 모델 출시",
    "RAG(검색증강생성) 기술 및 프레임워크 소식",
    "AI 에이전트 및 에이전틱 워크플로우",
]

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
ARXIV_MAX_RESULTS = 6


def validate():
    """필수 키가 비어있으면 친절하게 알려주고 종료."""
    required = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    missing = [k for k, v in required.items() if not v or "붙여넣기" in v]
    if missing:
        raise SystemExit(
            "[설정 오류] .env 파일에 다음 값을 채워주세요: " + ", ".join(missing)
        )

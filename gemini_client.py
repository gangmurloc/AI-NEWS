"""Gemini 호출 공통 로직 (재시도 포함). web_research.py, summarizer.py 에서 공용으로 사용."""
import time
from google import genai
from google.genai import errors as genai_errors
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)

# 텔레그램 legacy Markdown은 *굵게*(별표 1개)만 지원하고 **, ###, --- 는 모른다.
# 이 규칙 없이는 GitHub 스타일 마크다운이 그대로 별표/기호로 노출된다.
TELEGRAM_FORMAT_RULES = """서식 규칙 (텔레그램 전송용, 반드시 지킬 것):
- 굵게는 별표 1개로만: *이렇게* (별표 2개 **이렇게** 는 금지)
- #, ##, ### 같은 마크다운 제목 문법 쓰지 말 것
- --- 같은 구분선 쓰지 말 것
- 번호 목록은 "1) 제목" 형식으로, 마크다운 굵게 헤더 없이 작성
- 링크는 그냥 URL만 적을 것 (마크다운 링크 문법 [텍스트](URL) 금지)"""


def generate(prompt: str, retries: int = 2, base_delay: float = 20.0) -> str:
    """429(할당량 초과) 발생 시 잠깐 대기 후 재시도. 그래도 실패하면 예외를 그대로 던짐."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
            )
            return resp.text
        except genai_errors.APIError as e:
            last_error = e
            if getattr(e, "code", None) == 429 and attempt < retries:
                time.sleep(base_delay)
                continue
            raise
    raise last_error

"""Gemini 호출 공통 로직 (재시도 포함). web_research.py, summarizer.py 에서 공용으로 사용."""
import time
from google import genai
from google.genai import errors as genai_errors
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)


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

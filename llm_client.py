"""LLM 호출 공통 로직 (재시도 포함). OpenAI 호환 게이트웨이 사용.
web_research.py, summarizer.py, highlights.py 에서 공용으로 사용."""
import time
import requests
from openai import OpenAI, APIStatusError
import config

client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)

# 텔레그램 legacy Markdown은 *굵게*(별표 1개)만 지원하고 **, ###, --- 는 모른다.
# 이 규칙 없이는 GitHub 스타일 마크다운이 그대로 별표/기호로 노출된다.
TELEGRAM_FORMAT_RULES = """서식 규칙 (텔레그램 전송용, 반드시 지킬 것):
- 굵게는 별표 1개로만: *이렇게* (별표 2개 **이렇게** 는 금지)
- #, ##, ### 같은 마크다운 제목 문법 쓰지 말 것
- --- 같은 구분선 쓰지 말 것
- 번호 목록은 "1) 제목" 형식으로, 마크다운 굵게 헤더 없이 작성
- 링크는 그냥 URL만 적을 것 (마크다운 링크 문법 [텍스트](URL) 금지)"""


# 재시도할 가치가 있는 일시적 오류: 429(할당량 초과), 503(서버 과부하, "나중에 다시 시도" 안내가 붙음)
RETRYABLE_CODES = (429, 503)


def generate(prompt: str, retries: int = 4, base_delay: float = 60.0) -> str:
    """일시적 오류(429/503) 발생 시 잠깐 대기 후 재시도. 그래도 실패하면 예외를 그대로 던짐.

    분당 요청 제한(RPM)은 보통 60초면 풀리므로 대기 시간을 60초로 잡음.
    다만 이건 '분당 제한'에만 효과가 있고, 하루/계정 전체 할당량이 소진된 경우엔
    재시도해도 소용없으므로 무한 재시도는 하지 않고 몇 번 시도 후 포기함."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        except APIStatusError as e:
            last_error = e
            if e.status_code in RETRYABLE_CODES and attempt < retries:
                time.sleep(base_delay)
                continue
            raise
    raise last_error


def get_credit_balance() -> dict | None:
    """factchat 게이트웨이 전용 엔드포인트로 남은 크레딧을 조회 (OpenAI 표준 API가 아님).
    watchdog.py가 크레딧 소진 전에 미리 경고하는 데 사용. 다른 OpenAI 호환 게이트웨이로 바꾸면
    이 엔드포인트는 없을 수 있으니, 실패해도 예외를 던지지 않고 None을 반환."""
    try:
        resp = requests.get(
            f"{config.LLM_BASE_URL}/credits/",
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

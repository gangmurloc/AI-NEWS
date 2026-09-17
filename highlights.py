"""오늘 브리핑 전체에서 가장 중요한 항목 3개를 뽑아 정리."""
from llm_client import generate, TELEGRAM_FORMAT_RULES


def summarize_top3(candidates: list) -> str:
    raw = "\n".join(
        f"- {c['title']} ({c['link']})"
        for c in candidates
        if c.get("title") and c.get("link")
    )
    if not raw:
        return ""

    prompt = f"""아래는 오늘 브리핑에 실린 국내 AI 기회정보, 뉴스, 논문, 오픈소스 후보 전체 목록이야.
이 중 전반적으로 가장 중요하거나 임팩트가 큰 항목 3개를 골라 "오늘의 Top 3"로 요약해줘.

규칙:
- 정확히 3개 선정 (후보가 3개 미만이면 있는 만큼만)
- 각 항목: 제목(한국어로 번역) + 왜 중요한지 1문장 + 링크
- 목록에 없는 내용은 지어내지 말 것

{TELEGRAM_FORMAT_RULES}

후보 목록:
{raw}"""
    try:
        return generate(prompt)
    except Exception:
        # 실패해도 나머지 브리핑(토픽별 요약, 논문)은 이미 만들어졌으니 이 섹션만 조용히 생략
        return ""

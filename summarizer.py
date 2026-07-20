"""수집한 논문을 Gemini(무료 티어)로 읽기 쉽게 요약."""
from gemini_client import generate, TELEGRAM_FORMAT_RULES


def summarize_papers(papers) -> str:
    if not papers:
        return "오늘 새로운 논문을 찾지 못했습니다."

    raw = "\n\n".join(
        f"제목: {p['title']}\n저자: {p['authors']}\n초록: {p['summary']}\n링크: {p['link']}"
        for p in papers
    )
    prompt = f"""아래는 arXiv, OpenAlex, Semantic Scholar에서 모은 최근 논문 후보 목록이야.
소스가 여러 곳이라 학회지 게재료만 노린 저품질 저널 논문이나 관련성 낮은 논문도 섞여 있을 수 있어.

규칙:
- 실질적으로 흥미롭거나 중요한 논문만 골라서 최대 8개 선별 (억지로 다 채우지 말 것)
- 저품질/약탈적 저널로 보이거나 초록이 부실한 논문은 제외
- 비전공자도 이해할 수 있게 각 논문을 다음 형식으로 한국어 정리:
  - 한 줄 핵심
  - 왜 중요한지 1문장
  - 링크

{TELEGRAM_FORMAT_RULES}

논문 후보 목록:
{raw}"""
    try:
        return generate(prompt)
    except Exception as e:
        # Gemini가 실패하면 필터링 전 원본(다국어 포함)을 그대로 보내지 않고, 제목+링크만 간단히
        title_links = "\n".join(f"- {p['title']} ({p['link']})" for p in papers)
        return f"(논문 요약 실패: {type(e).__name__} — 잠시 후 다시 시도됩니다)\n\n{title_links}"

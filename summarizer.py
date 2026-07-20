"""수집한 논문을 Gemini(무료 티어)로 읽기 쉽게 요약."""
from gemini_client import generate, TELEGRAM_FORMAT_RULES


def summarize_papers(papers) -> str:
    if not papers:
        return "오늘 새로운 논문을 찾지 못했습니다."

    raw = "\n\n".join(
        f"제목: {p['title']}\n저자: {p['authors']}\n초록: {p['summary']}\n링크: {p['link']}"
        for p in papers
    )
    prompt = f"""아래는 오늘 arXiv 최신 논문 목록이야.
비전공자도 이해할 수 있게 각 논문을 다음 형식으로 한국어 정리해줘:
- 한 줄 핵심
- 왜 중요한지 1문장
- 링크

{TELEGRAM_FORMAT_RULES}

논문 목록:
{raw}"""
    try:
        return generate(prompt)
    except Exception as e:
        return f"(논문 요약 실패: {e})\n\n원본 목록:\n{raw}"

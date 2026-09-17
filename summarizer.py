"""수집한 논문을 LLM으로 읽기 쉽게 요약."""
import config
from llm_client import generate, TELEGRAM_FORMAT_RULES


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
- 실질적으로 흥미롭거나 중요한 논문만 최대 {config.PAPER_FINAL_MAX_RESULTS}개 선별
- 품질 기준을 만족하는 논문이 적으면 억지로 채우지 말 것
- 저품질/약탈적 저널로 보이거나 초록이 부실한 논문은 제외
- 비전공자도 이해할 수 있게 각 논문을 다음 형식으로 한국어 정리:
  1) 제목(한국어로 번역)
  - 핵심 요약: 무엇을 했고 결과가 무엇인지 2~3문장
  - 한계: 이 논문의 한계나 제약(데이터 규모, 검증 방식, 일반화 가능성 등) 1~2문장.
    초록에서 한계를 명시적으로 언급하지 않았다면 "초록에 한계 언급 없음"이라고 쓸 것 (지어내지 말 것)
  - 링크

{TELEGRAM_FORMAT_RULES}

논문 후보 목록:
{raw}"""
    try:
        return generate(prompt)
    except Exception as e:
        # LLM 호출이 실패하면 필터링 전 원본(다국어 포함)을 그대로 보내지 않고, 제목+링크만 간단히
        title_links = "\n".join(
            f"- {p['title']} ({p['link']})"
            for p in papers[: config.PAPER_FINAL_MAX_RESULTS]
        )
        return f"(논문 요약 실패: {type(e).__name__} — 잠시 후 다시 시도됩니다)\n\n{title_links}"

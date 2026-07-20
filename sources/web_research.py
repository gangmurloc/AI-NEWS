"""OpenAI 웹 검색으로 주제별 최신 뉴스/이슈를 수집."""
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


def research_topic(topic: str) -> str:
    prompt = f"""'{topic}' 에 대해 웹에서 오늘 기준 가장 중요하고 새로운 소식을 검색해줘.

규칙:
- 핵심 이슈 3~5개만 선별
- 각 항목은 [제목] + 2문장 요약 + 출처 링크
- 오래된 내용/중복 제외, 최신 위주
- 한국어로 작성"""
    try:
        # OpenAI Responses API + 웹 검색 도구
        resp = client.responses.create(
            model=config.OPENAI_MODEL,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        return resp.output_text
    except Exception as e:
        # 웹검색 도구를 못 쓰는 환경/버전이면 일반 답변으로 폴백
        try:
            resp = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content + "\n(주의: 웹검색 없이 생성됨)"
        except Exception as e2:
            return f"({topic} 수집 실패: {e2})"

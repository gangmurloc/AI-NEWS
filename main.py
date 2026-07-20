"""전체 흐름: 수집 → 요약 → 텔레그램 전송. 이 파일을 실행하면 됩니다."""
from datetime import date
import config
from sources.web_research import research_topic
from sources.arxiv_papers import fetch_recent_papers
from summarizer import summarize_papers
from telegram_sender import send_message


def build_digest() -> str:
    today = date.today().isoformat()
    parts = [f"📰 *데일리 브리핑* — {today}"]

    # 1) 관심 주제별 웹 리서치
    for topic in config.TOPICS:
        print(f"  - '{topic}' 검색 중...")
        parts.append(f"\n━━━━━━━━━━━━\n🔎 *{topic}*\n")
        parts.append(research_topic(topic))

    # 2) 최신 논문
    print("  - 논문 수집 중...")
    parts.append("\n━━━━━━━━━━━━\n📄 *오늘의 논문*\n")
    papers = fetch_recent_papers()
    parts.append(summarize_papers(papers))

    return "\n".join(parts)


def main():
    config.validate()
    print("브리핑 생성 시작...")
    digest = build_digest()
    print("텔레그램 전송 중...")
    send_message(digest)
    print("완료! 텔레그램을 확인하세요.")


if __name__ == "__main__":
    main()

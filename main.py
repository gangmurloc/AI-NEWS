"""전체 흐름: 수집 → 요약 → 텔레그램 전송. 이 파일을 실행하면 됩니다."""
from datetime import date
import config
import history
from sources.web_research import fetch_topic_articles, summarize_topic
from sources.arxiv_papers import fetch_recent_papers
from summarizer import summarize_papers
from telegram_sender import send_message


def build_digest():
    """(브리핑 텍스트, 이번에 사용된 링크 목록) 을 반환."""
    today = date.today().isoformat()
    parts = [f"📰 *데일리 브리핑* — {today}"]
    used_links = []

    # 1) 관심 주제별 웹 리서치
    for topic in config.TOPICS:
        print(f"  - '{topic['label']}' 검색 중...")
        articles = fetch_topic_articles(topic["query"])
        used_links.extend(articles)
        parts.append(f"\n━━━━━━━━━━━━\n🔎 *{topic['label']}*\n")
        parts.append(summarize_topic(articles, topic["label"]))

    # 2) 최신 논문
    print("  - 논문 수집 중...")
    papers = fetch_recent_papers()
    used_links.extend(papers)
    parts.append("\n━━━━━━━━━━━━\n📄 *오늘의 논문*\n")
    parts.append(summarize_papers(papers))

    return "\n".join(parts), used_links


def main():
    config.validate()
    print("브리핑 생성 시작...")
    try:
        digest, used_links = build_digest()
        print("텔레그램 전송 중...")
        send_message(digest)
        history.mark_sent(used_links)
        print("완료! 텔레그램을 확인하세요.")
    except Exception as e:
        # 파이프라인이 죽어도 사용자가 GitHub Actions를 직접 확인하지 않아도 되도록 알림
        try:
            send_message(f"⚠️ 데일리 브리핑 생성 중 오류가 발생했습니다.\n\n{type(e).__name__}: {e}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()

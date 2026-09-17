"""전체 흐름: 수집 → 요약 → 텔레그램 전송. 이 파일을 실행하면 됩니다."""
import json
from datetime import datetime
from pathlib import Path
import config
import history
from sources.web_research import fetch_topic_articles, summarize_core_news
from sources.outlet_feeds import fetch_outlet_articles
from sources.korea_opportunities import fetch_opportunities, summarize_opportunities
from sources.papers import fetch_all_papers
from sources.github_trending import fetch_trending_repos, format_trending
from summarizer import summarize_papers
from highlights import summarize_top3
from telegram_sender import send_message

ARCHIVE_DIR = Path(__file__).parent / "archive"
LAST_SUCCESS_FILE = Path(__file__).parent / "last_success.json"


def _referenced_items(items: list[dict], *texts: str) -> list[dict]:
    """LLM 결과에 실제로 링크가 실린 항목만 발송 이력 대상으로 반환한다."""
    combined = "\n".join(texts)
    referenced = []
    for item in items:
        links = [item.get("link", ""), *item.get("application_links", [])]
        if any(link and link in combined for link in links):
            referenced.append(item)
    return referenced


def build_digest():
    """(브리핑 텍스트, 이번에 사용된 링크 목록) 을 반환."""
    today = config.today_kst().isoformat()
    parts = [f"📡 *AI 기회정보 & 핵심 브리핑* — {today}"]
    used_links = []
    all_candidates = []
    seen_links = set()  # 앞선 토픽이 이미 채택한 링크 (여러 토픽에 같은 기사가 중복 등장하는 것 방지)

    # 1) 국내 AI 대회/공모전/교육/지원사업
    print("  - 국내 AI 기회정보 수집 중...")
    opportunities = fetch_opportunities()
    all_candidates.extend(opportunities)
    parts.append("\n━━━━━━━━━━━━\n🏆 *국내 AI 대회·공모전·모집*\n")
    opportunity_summary = summarize_opportunities(opportunities)
    parts.append(opportunity_summary)
    used_links.extend(_referenced_items(opportunities, opportunity_summary))

    # 2) 관심 주제 뉴스 후보를 모두 합친 뒤 핵심만 한 번에 선별
    print("  - 신뢰 매체 RSS 수집 중...")
    outlet_articles = fetch_outlet_articles()
    news_candidates = []
    for topic in config.TOPICS:
        print(f"  - '{topic['label']}' 검색 중...")
        articles = fetch_topic_articles(topic["query"], topic["hn_query"], outlet_articles, seen_links)
        seen_links.update(a["link"] for a in articles)
        news_candidates.extend(articles)
    news_candidates.sort(key=lambda item: item.get("published_ts", 0), reverse=True)
    all_candidates.extend(news_candidates)
    parts.append("\n━━━━━━━━━━━━\n📰 *핵심 AI 뉴스*\n")
    news_summary = summarize_core_news(news_candidates)
    parts.append(news_summary)
    used_links.extend(_referenced_items(news_candidates, news_summary))

    # 3) 최신 논문 (arXiv + OpenAlex + Semantic Scholar)
    print("  - 논문 수집 중...")
    papers = fetch_all_papers()
    all_candidates.extend(papers)
    parts.append("\n━━━━━━━━━━━━\n📄 *오늘의 논문*\n")
    paper_summary = summarize_papers(papers)
    parts.append(paper_summary)
    used_links.extend(_referenced_items(papers, paper_summary))

    # 4) 떠오르는 오픈소스 (GitHub)
    print("  - GitHub 트렌딩 레포 수집 중...")
    trending = fetch_trending_repos()
    all_candidates.extend(trending)
    parts.append("\n━━━━━━━━━━━━\n🔧 *떠오르는 오픈소스 (GitHub)*\n")
    trending_summary = format_trending(trending)
    parts.append(trending_summary)
    used_links.extend(_referenced_items(trending, trending_summary))

    # 5) 오늘의 Top 3 (기회정보+뉴스+논문+오픈소스 통틀어 가장 중요한 항목)
    print("  - Top 3 선정 중...")
    top3 = summarize_top3(all_candidates)
    if top3:
        parts.insert(1, f"\n⭐ *오늘의 Top 3*\n\n{top3}\n")
        used_links.extend(_referenced_items(all_candidates, top3))

    used_links = list({item["link"]: item for item in used_links}.values())

    return "\n".join(parts), used_links


def _save_archive(digest: str):
    """과거 브리핑을 날짜별 markdown으로 저장 (텔레그램 채팅 스크롤 없이 다시 볼 수 있도록)."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    today = config.today_kst().isoformat()
    (ARCHIVE_DIR / f"{today}.md").write_text(digest, encoding="utf-8")


def _mark_success():
    """워치독(watchdog.py)이 '며칠째 브리핑이 안 왔는지' 판단할 수 있도록 마지막 성공 시각 기록."""
    LAST_SUCCESS_FILE.write_text(
        json.dumps({"timestamp": datetime.now(config.KST).isoformat()}),
        encoding="utf-8",
    )


def main():
    config.validate()
    print("브리핑 생성 시작...")
    try:
        digest, used_links = build_digest()
        print("텔레그램 전송 중...")
        send_message(digest)
        history.mark_sent(used_links)
        _save_archive(digest)
        _mark_success()
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

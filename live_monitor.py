"""새 국내 AI 기회정보와 핵심 뉴스를 주기적으로 확인해 텔레그램으로 보낸다."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import socket
import sys
import time

import config
import history
from main import _referenced_items
from opportunity_tracker import (
    collect_deadline_reminders,
    format_changes,
    format_reminders,
    load_state,
    mark_reminders_sent,
    refresh_due_records,
    save_state,
    upsert_items,
)
from sources.korea_opportunities import (
    discover_opportunities,
    enrich_opportunities,
    summarize_opportunities,
)
from sources.outlet_feeds import fetch_outlet_articles
from sources.web_research import fetch_topic_articles, summarize_core_news
from telegram_sender import send_message


BASE_DIR = Path(__file__).parent
SEEN_FILE = BASE_DIR / "live_seen.json"
CURSOR_FILE = BASE_DIR / "live_cursor.json"
LOG_FILE = BASE_DIR / "live_monitor.log"
SEEN_RETENTION_DAYS = 60
CURSOR_OVERLAP_SECONDS = 10 * 60
MAX_FUTURE_SECONDS = 10 * 60
LOCK_PORT = 47653


def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("live-monitor")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger


LOGGER = _setup_logging()


def _load_seen() -> dict[str, str]:
    if not SEEN_FILE.exists():
        return {}
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_seen(items: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=SEEN_RETENTION_DAYS)
    seen = {}
    for link, timestamp in _load_seen().items():
        try:
            if datetime.fromisoformat(timestamp) >= cutoff:
                seen[link] = timestamp
        except (TypeError, ValueError):
            continue
    for item in items:
        link = item.get("link")
        if link:
            seen[link] = now.isoformat()
    SEEN_FILE.write_text(
        json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_cursor() -> float | None:
    if not CURSOR_FILE.exists():
        return None
    try:
        data = json.loads(CURSOR_FILE.read_text(encoding="utf-8"))
        return float(data["checked_at_ts"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _save_cursor(timestamp: float | None = None) -> None:
    checked_at = timestamp if timestamp is not None else time.time()
    CURSOR_FILE.write_text(
        json.dumps({"checked_at_ts": checked_at}, indent=2), encoding="utf-8"
    )


def _after_cursor(items: list[dict], cursor: float | None) -> list[dict]:
    if cursor is None:
        return items
    lower_bound = cursor - CURSOR_OVERLAP_SECONDS
    upper_bound = time.time() + MAX_FUTURE_SECONDS
    return [
        item
        for item in items
        if lower_bound < item.get("published_ts", 0) <= upper_bound
    ]


def _collect_news(exclude_links: set[str]) -> list[dict]:
    outlet_articles = fetch_outlet_articles()
    candidates = []
    seen_this_run = set(exclude_links)
    for topic in config.TOPICS:
        articles = fetch_topic_articles(
            topic["query"], topic["hn_query"], outlet_articles, seen_this_run
        )
        candidates.extend(articles)
        seen_this_run.update(item["link"] for item in articles)
    candidates.sort(key=lambda item: item.get("published_ts", 0), reverse=True)
    return candidates


def build_live_update() -> tuple[str, list[dict], list[dict], list[dict]]:
    """전송문, 실제 전송 항목, 처리 후보, 추적할 공고를 반환한다."""
    seen_links = set(_load_seen())
    opportunity_candidates = discover_opportunities(seen_links)
    news_candidates = _collect_news(seen_links)
    cursor = _load_cursor()
    opportunity_candidates = _after_cursor(opportunity_candidates, cursor)
    news_candidates = _after_cursor(news_candidates, cursor)
    processed = opportunity_candidates + news_candidates
    if not processed:
        return "", [], [], []

    opportunities = enrich_opportunities(
        opportunity_candidates[: config.OPPORTUNITY_MAX_CANDIDATES]
    )
    news = news_candidates[: config.CORE_NEWS_MAX_CANDIDATES]

    sections = []
    sent_items = []
    tracked_opportunities = []
    if opportunities:
        summary = summarize_opportunities(opportunities)
        selected = _referenced_items(opportunities, summary)
        if selected:
            sections.append(f"🏆 *새 국내 AI 대회·공모전·모집*\n\n{summary}")
            sent_items.extend(selected)
            tracked_opportunities.extend(selected)

    if news:
        summary = summarize_core_news(news)
        selected = _referenced_items(news, summary)
        if selected:
            sections.append(f"📰 *새 핵심 AI 뉴스*\n\n{summary}")
            sent_items.extend(selected)

    if not sections:
        return "", [], processed, tracked_opportunities

    timestamp = datetime.now(config.KST).strftime("%Y-%m-%d %H:%M")
    message = f"📡 *AI 실시간 업데이트* — {timestamp}\n\n" + "\n\n━━━━━━━━━━━━\n\n".join(sections)
    unique_sent = list({item["link"]: item for item in sent_items}.values())
    return message, unique_sent, processed, tracked_opportunities


def check_once() -> bool:
    message, sent_items, processed, tracked_opportunities = build_live_update()
    state = load_state()
    changes, new_keys = upsert_items(state, tracked_opportunities)
    changes.extend(refresh_due_records(state))
    reminders = collect_deadline_reminders(state, new_keys)

    alert_sections = []
    if changes:
        alert_sections.append(f"🔄 *공고 변경 감지*\n\n{format_changes(changes)}")
    if reminders:
        alert_sections.append(f"⏰ *마감 재알림*\n\n{format_reminders(reminders)}")
    if alert_sections:
        alerts = "\n\n━━━━━━━━━━━━\n\n".join(alert_sections)
        if message:
            message = f"{message}\n\n━━━━━━━━━━━━\n\n{alerts}"
        else:
            timestamp = datetime.now(config.KST).strftime("%Y-%m-%d %H:%M")
            message = f"📡 *AI 기회정보 알림* — {timestamp}\n\n{alerts}"

    if message:
        send_message(message)
        history.mark_sent(sent_items)
        mark_reminders_sent(state, reminders)
        LOGGER.info(
            "텔레그램 전송 완료: 신규 %d건, 변경 %d건, 마감알림 %d건",
            len(sent_items), len(changes), len(reminders),
        )
    elif processed:
        LOGGER.info("후보 %d건 확인, 전송 기준을 만족한 항목 없음", len(processed))
    else:
        LOGGER.info("새 후보 및 마감 알림 없음")

    save_state(state)
    if processed:
        _save_seen(processed)
    _save_cursor()
    return bool(message)


def prime_seen() -> int:
    """현재 검색되는 기존 후보를 전송 없이 기준선으로 기록한다."""
    seen_links = set(_load_seen())
    candidates = discover_opportunities(seen_links) + _collect_news(seen_links)
    _save_seen(candidates)
    _save_cursor()
    LOGGER.info("실시간 기준선 갱신: %d건", len(candidates))
    return len(candidates)


def bootstrap_opportunity_tracking() -> int:
    """현재 검색되는 공고를 알림 없이 변경/마감 추적 목록에 등록한다."""
    candidates = discover_opportunities(include_sent=True)
    opportunities = enrich_opportunities(
        candidates[: config.OPPORTUNITY_MAX_CANDIDATES]
    )
    unique_opportunities = []
    seen_application_links = set()
    for item in opportunities:
        application_link = item.get("application_link") or item.get("link")
        if application_link in seen_application_links:
            continue
        seen_application_links.add(application_link)
        unique_opportunities.append(item)
    state = {"records": {}}
    upsert_items(state, unique_opportunities)
    save_state(state)
    LOGGER.info("공고 추적 기준선 등록: %d건", len(state["records"]))
    return len(state["records"])


def _acquire_single_instance_lock() -> socket.socket:
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
        lock.listen(1)
    except OSError as error:
        lock.close()
        raise SystemExit("실시간 모니터가 이미 실행 중입니다.") from error
    return lock


def run_forever() -> None:
    lock = _acquire_single_instance_lock()
    if _load_cursor() is None:
        prime_seen()
    LOGGER.info(
        "실시간 모니터 시작: %d분 간격", config.LIVE_POLL_INTERVAL_MINUTES
    )
    try:
        while True:
            started = time.monotonic()
            try:
                check_once()
            except Exception:
                LOGGER.exception("실시간 확인 실패")
            elapsed = time.monotonic() - started
            time.sleep(max(1, config.LIVE_POLL_INTERVAL_SECONDS - elapsed))
    except KeyboardInterrupt:
        LOGGER.info("실시간 모니터 종료")
    finally:
        lock.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="한 번만 확인하고 종료")
    parser.add_argument(
        "--prime", action="store_true", help="현재 후보를 전송 없이 확인 완료로 기록"
    )
    parser.add_argument(
        "--bootstrap-opportunities",
        action="store_true",
        help="현재 공고를 마감/변경 추적 목록에 등록",
    )
    args = parser.parse_args()
    config.validate()
    if args.bootstrap_opportunities:
        bootstrap_opportunity_tracking()
    elif args.prime:
        prime_seen()
    elif args.once:
        check_once()
    else:
        run_forever()


if __name__ == "__main__":
    main()

"""AI 대회 공고의 마감 재알림과 원문 변경을 추적한다."""
from datetime import datetime
from difflib import SequenceMatcher
import json
from pathlib import Path
import re

import config
from sources.korea_opportunities import (
    build_opportunity_record,
    extract_page_details,
    is_excluded_local_opportunity,
)


STATE_FILE = Path(__file__).parent / "opportunity_state.json"
TRACKED_FIELDS = {
    "deadline": "접수 마감일",
    "application_link": "신청 링크",
    "checklist": "준비 체크리스트",
}


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"records": {}}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("records"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"records": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _record_key(record: dict) -> str:
    return record.get("source_link", "").split("#", 1)[0]


def _now_iso() -> str:
    return datetime.now(config.KST).isoformat()


def _should_track(record: dict) -> bool:
    searchable = f"{record.get('title', '')} {record.get('content_text', '')[:500]}"
    if re.search(r"직원\s*대상|임직원|사내\s*(?:대회|공모)", searchable):
        return False
    if is_excluded_local_opportunity(
        record.get("title", ""), record.get("content_text", "")
    ):
        return False
    deadline = record.get("deadline")
    if deadline:
        try:
            if datetime.strptime(deadline, "%Y-%m-%d").date() < config.today_kst():
                return False
        except ValueError:
            return False
    return True


def _initial_reminder_tokens(record: dict) -> list[str]:
    deadline = record.get("deadline")
    if not deadline:
        return []
    try:
        days_left = (datetime.strptime(deadline, "%Y-%m-%d").date() - config.today_kst()).days
    except ValueError:
        return []
    if days_left in config.OPPORTUNITY_REMINDER_DAYS:
        return [f"{deadline}:D-{days_left}"]
    return []


def _describe_changes(old: dict, new: dict) -> list[str]:
    old_text = re.sub(r"\s+", " ", old.get("content_text", "")).strip()
    new_text = re.sub(r"\s+", " ", new.get("content_text", "")).strip()
    if old.get("content_hash") == new.get("content_hash"):
        return []
    if min(len(old_text), len(new_text)) < config.OPPORTUNITY_MAJOR_CHANGE_MIN_CHARS:
        return []

    similarity = SequenceMatcher(None, old_text, new_text, autojunk=False).ratio()
    changed_chars = int(max(len(old_text), len(new_text)) * (1 - similarity))
    if (
        similarity >= config.OPPORTUNITY_MAJOR_CHANGE_MAX_SIMILARITY
        or changed_chars < config.OPPORTUNITY_MAJOR_CHANGE_MIN_CHARS
    ):
        return []

    changes = [f"공고 핵심 내용이 대폭 변경됨 (본문 유사도 {similarity:.0%})"]
    for field, label in TRACKED_FIELDS.items():
        old_value = old.get(field) or "확인 필요"
        new_value = new.get(field) or "확인 필요"
        if old_value != new_value:
            if isinstance(old_value, list):
                old_value = ", ".join(old_value)
                new_value = ", ".join(new_value)
            changes.append(f"{label}: {old_value} → {new_value}")
    return changes


def upsert_items(state: dict, items: list[dict]) -> tuple[list[dict], set[str]]:
    """새 공고를 등록하고 기존 공고의 핵심 변경사항을 반환한다."""
    changes = []
    new_keys = set()
    now = _now_iso()
    for item in items:
        record = build_opportunity_record(item)
        key = _record_key(record)
        if not _should_track(record):
            if key:
                state["records"].pop(key, None)
            continue
        if not key:
            continue
        previous = state["records"].get(key)
        if previous:
            differences = _describe_changes(previous, record)
            if differences:
                changes.append({"title": record["title"], "link": record["application_link"], "differences": differences})
            record["first_seen_at"] = previous.get("first_seen_at", now)
            record["sent_reminders"] = previous.get("sent_reminders", [])
        else:
            record["first_seen_at"] = now
            record["sent_reminders"] = _initial_reminder_tokens(record)
            new_keys.add(key)
        record["last_checked_at"] = now
        state["records"][key] = record
    return changes, new_keys


def refresh_due_records(state: dict) -> list[dict]:
    """일정 시간이 지난 추적 공고를 다시 읽고 의미 있는 변경만 반환한다."""
    now = datetime.now(config.KST)
    due = []
    for key, record in list(state["records"].items()):
        if not _should_track(record):
            state["records"].pop(key, None)
            continue
        try:
            checked = datetime.fromisoformat(record.get("last_checked_at", ""))
        except (TypeError, ValueError):
            checked = datetime.min.replace(tzinfo=config.KST)
        age_minutes = (now - checked).total_seconds() / 60
        if age_minutes >= config.OPPORTUNITY_REFRESH_MINUTES:
            due.append((key, record))
    due = due[: config.OPPORTUNITY_REFRESH_BATCH_SIZE]

    changes = []
    for key, previous in due:
        body, application_links = extract_page_details(previous["source_link"])
        if not body:
            previous["last_checked_at"] = now.isoformat()
            continue
        item = {
            "title": previous["title"],
            "link": previous["source_link"],
            "body": body,
            "application_links": application_links or [previous.get("application_link", "")],
        }
        current = build_opportunity_record(item)
        if not _should_track(current):
            state["records"].pop(key, None)
            continue
        differences = _describe_changes(previous, current)
        if differences:
            changes.append({"title": current["title"], "link": current["application_link"], "differences": differences})
        current["first_seen_at"] = previous.get("first_seen_at", now.isoformat())
        current["sent_reminders"] = previous.get("sent_reminders", [])
        current["last_checked_at"] = now.isoformat()
        state["records"][key] = current
    return changes


def collect_deadline_reminders(state: dict, skip_keys: set[str] = frozenset()) -> list[dict]:
    today = config.today_kst()
    reminders = []
    for key, record in state["records"].items():
        if key in skip_keys or not record.get("deadline") or not _should_track(record):
            continue
        try:
            deadline = datetime.strptime(record["deadline"], "%Y-%m-%d").date()
        except ValueError:
            continue
        days_left = (deadline - today).days
        token = f"{record['deadline']}:D-{days_left}"
        if days_left in config.OPPORTUNITY_REMINDER_DAYS and token not in record.get("sent_reminders", []):
            reminders.append({"key": key, "token": token, "days_left": days_left, **record})
    return reminders


def mark_reminders_sent(state: dict, reminders: list[dict]) -> None:
    for reminder in reminders:
        record = state["records"].get(reminder["key"])
        if record and reminder["token"] not in record["sent_reminders"]:
            record["sent_reminders"].append(reminder["token"])


def format_changes(changes: list[dict]) -> str:
    blocks = []
    for index, change in enumerate(changes, 1):
        lines = "\n".join(f"- {item}" for item in change["differences"])
        blocks.append(f"{index}) *{change['title']}*\n{lines}\n- 확인: {change['link']}")
    return "\n\n".join(blocks)


def format_reminders(reminders: list[dict]) -> str:
    blocks = []
    for index, reminder in enumerate(reminders, 1):
        d_day = "D-Day" if reminder["days_left"] == 0 else f"D-{reminder['days_left']}"
        checklist = "\n".join(f"  □ {item}" for item in reminder.get("checklist", []))
        blocks.append(
            f"{index}) *{reminder['title']}* — {d_day} ({reminder['deadline']})\n"
            f"- 준비 체크리스트\n{checklist}\n- 신청: {reminder['application_link']}"
        )
    return "\n\n".join(blocks)

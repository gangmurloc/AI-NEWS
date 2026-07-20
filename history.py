"""이미 보낸 기사/논문 링크를 저장소에 기록해서 며칠 내 중복 전송을 방지."""
import json
import os
from datetime import datetime, timedelta, timezone

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "sent_history.json")

# 이 기간 안에 이미 보낸 링크는 다시 보내지 않음
RETENTION_DAYS = 7


def _load() -> dict:
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def filter_unsent(items: list, link_key: str = "link") -> list:
    """이미 보낸 적 있는 링크(보존 기간 이내)는 제외하고 반환."""
    sent = _load()
    return [item for item in items if item[link_key] not in sent]


def mark_sent(items: list, link_key: str = "link"):
    """이번에 실제로 사용한 링크들을 기록하고, 보존 기간이 지난 오래된 기록은 정리."""
    sent = _load()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=RETENTION_DAYS)

    sent = {
        link: ts for link, ts in sent.items()
        if datetime.fromisoformat(ts) >= cutoff
    }
    for item in items:
        sent[item[link_key]] = now.isoformat()

    _save(sent)

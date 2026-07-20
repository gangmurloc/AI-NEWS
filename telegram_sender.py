"""텔레그램으로 메시지 전송 (4096자 제한 자동 분할)."""
import requests
import config

TELEGRAM_LIMIT = 4000  # 여유 있게


def send_message(text: str):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    for chunk in _split(text, TELEGRAM_LIMIT):
        resp = requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
        if not resp.ok:
            # 마크다운 파싱 오류 시 일반 텍스트로 재시도
            resp = requests.post(url, data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            })
        if not resp.ok:
            # 여기서 예외를 던지지 않으면 전송이 실패해도 호출자가 알 방법이 없고,
            # main.py가 실제로는 못 보낸 링크를 "보낸 것"으로 기록해버린다.
            raise RuntimeError(f"텔레그램 전송 실패 ({resp.status_code}): {resp.text[:300]}")


def _split(text, limit):
    buf = ""
    for line in text.split("\n"):
        # 한 줄 자체가 limit보다 길면(드문 경우) 그 줄만 강제로 잘라서 보냄
        while len(line) > limit:
            if buf:
                yield buf
                buf = ""
            yield line[:limit]
            line = line[limit:]

        if len(buf) + len(line) + 1 > limit:
            if buf:
                yield buf
            buf = ""
        buf += line + "\n"
    if buf:
        yield buf

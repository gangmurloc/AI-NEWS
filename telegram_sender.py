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
            requests.post(url, data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            })


def _split(text, limit):
    buf = ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > limit:
            if buf:
                yield buf
            buf = ""
        buf += line + "\n"
    if buf:
        yield buf

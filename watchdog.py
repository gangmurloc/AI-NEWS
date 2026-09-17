"""메인 파이프라인(main.py)이 며칠째 실행되지 않고 있는지, 그리고 LLM 크레딧이 얼마 안 남았는지 감시.
daily.yml과 별도로, 이보다 늦게 도는 watchdog.yml 스케줄에서 실행됨.
(GitHub가 60일간 활동 없는 저장소의 스케줄 워크플로를 자동 비활성화하는 경우까지는 감지 못함 — 이건 코드로 해결 불가한
플랫폼 제약이라, 그 경우엔 저장소에 커밋 등 아무 활동이나 한 번 해줘서 스케줄을 다시 살려야 함)"""
from datetime import datetime, timedelta
from pathlib import Path
import json
import config
from llm_client import get_credit_balance
from telegram_sender import send_message

LAST_SUCCESS_FILE = Path(__file__).parent / "last_success.json"
MAX_SILENT_DAYS = 2


def _check_silence():
    if not LAST_SUCCESS_FILE.exists():
        return  # 아직 한 번도 성공한 적 없으면(최초 세팅 단계) 스킵

    data = json.loads(LAST_SUCCESS_FILE.read_text(encoding="utf-8"))
    last_success = datetime.fromisoformat(data["timestamp"])
    silent_for = datetime.now(config.KST) - last_success

    if silent_for > timedelta(days=MAX_SILENT_DAYS):
        send_message(
            f"⚠️ 데일리 브리핑이 {silent_for.days}일째 도착하지 않았습니다. "
            f"GitHub Actions 실행 로그를 확인해주세요."
        )


def _check_credits():
    """Gemini 키가 예고 없이 소진돼서 요약만 조용히 실패했던 것과 같은 상황을 미리 감지.
    이 게이트웨이 고유 엔드포인트라 다른 곳으로 바꾸면 balance가 None이 되고, 이 경우 조용히 스킵."""
    balance = get_credit_balance()
    if not balance:
        return

    total = balance.get("total") or {}
    quota = total.get("quota") or 0
    remaining = total.get("remaining")
    if not quota or remaining is None:
        return

    ratio = remaining / quota
    if ratio < config.LLM_CREDIT_ALERT_RATIO:
        renewal = (balance.get("monthly_allocated") or {}).get("renewal_date", "?")
        send_message(
            f"⚠️ LLM 크레딧이 얼마 남지 않았습니다 (남음: {remaining:.1f} / {quota:.0f}, "
            f"{ratio * 100:.1f}%). 다음 갱신일: {renewal}. "
            f"소진되면 요약이 조용히 실패하고 원본 링크만 전송되니 미리 확인해주세요."
        )


def main():
    config.validate()
    _check_silence()
    _check_credits()


if __name__ == "__main__":
    main()

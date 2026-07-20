"""텔레그램 chat_id 확인용 도우미.
사용법:
 1) .env 에 TELEGRAM_BOT_TOKEN 먼저 입력
 2) 텔레그램에서 내 봇을 찾아 아무 메시지나 전송 (예: 안녕)
 3) 이 파일 실행 → 출력된 chat_id 를 .env 에 넣기
"""
import requests
import config

url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
data = requests.get(url).json()

found = False
for u in data.get("result", []):
    msg = u.get("message") or u.get("edited_message")
    if msg:
        chat = msg["chat"]
        print(f"chat_id: {chat['id']}  |  이름: {chat.get('first_name', '')}")
        found = True

if not found:
    print("메시지를 못 찾았습니다. 봇에게 먼저 아무 메시지나 보낸 뒤 다시 실행하세요.")
    print("원본 응답:", data)

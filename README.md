# 📰 AI 데일리 브리핑 봇

매일 관심 주제의 뉴스/핫토픽과 최신 논문을 AI가 정리해서 **텔레그램**으로 보내줍니다.
**완전 무료** — Gemini 무료 티어 + Google News RSS + arXiv + 텔레그램 + GitHub Actions, 결제수단 등록 없이 동작합니다.

---

## 필요한 것 3가지 (전부 `.env` 한 곳에만 입력, 전부 무료 발급)

| 항목 | 발급처 |
|------|--------|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey (Google 계정만 있으면 무료 발급) |
| `TELEGRAM_BOT_TOKEN` | 텔레그램에서 `@BotFather` → `/newbot` |
| `TELEGRAM_CHAT_ID` | 아래 3-2단계에서 자동 확인 |

> 💡 코드는 이미 다 짜여 있습니다. **키만 넣으면 바로 동작**합니다.

---

## 설치 & 실행 (5단계)

### 1. 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 2. 설정 파일 만들기
`.env.example` 을 복사해서 `.env` 로 이름 바꾸고 키를 채웁니다.
```bash
cp .env.example .env      # 윈도우면: copy .env.example .env
```

### 3-1. 텔레그램 봇 만들기
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 이름 정하기
2. 나오는 **토큰**을 `.env` 의 `TELEGRAM_BOT_TOKEN` 에 입력

### 3-2. chat_id 알아내기
1. 방금 만든 내 봇을 검색해서 **아무 메시지나 전송** (예: "안녕")
2. 아래 실행 → 나온 숫자를 `.env` 의 `TELEGRAM_CHAT_ID` 에 입력
```bash
python get_chat_id.py
```

### 4. Gemini 키 입력
1. https://aistudio.google.com/apikey 접속 → Google 계정으로 로그인 → **Create API key** (무료, 카드 등록 불필요)
2. 발급받은 키를 `.env` 의 `GEMINI_API_KEY` 에 붙여넣기

### 5. 실행
```bash
python main.py
```
텔레그램에 브리핑이 도착하면 성공입니다. 🎉

---

## 관심 주제 바꾸기
현재 기본값은 **AI / LLM / RAG** 위주로 맞춰져 있습니다. `config.py` 파일의
`TOPICS`, `ARXIV_CATEGORIES`, `ARXIV_KEYWORDS` 를 수정하면 다른 분야로도 바꿀 수 있습니다.
```python
TOPICS = ["관심 주제 1", "관심 주제 2", ...]
ARXIV_CATEGORIES = ["cs.AI", "cs.CV"]   # cs.CL, stat.ML 등
ARXIV_KEYWORDS = ["large language model", "LLM", "RAG", ...]  # 초록에 포함될 키워드
```

---

## 매일 자동으로 받기 (택 1)

### 방법 A — GitHub Actions (추천, PC 안 켜도 됨)
1. GitHub에서 새 저장소를 만듭니다 (Public/Private 무관, README 없이 빈 저장소로).
2. 로컬 저장소를 연결하고 올립니다. (`.env` 는 올라가지 않습니다 — `.gitignore` 처리됨)
   ```bash
   git remote add origin https://github.com/<내계정>/<저장소이름>.git
   git branch -M main
   git push -u origin main
   ```
3. 저장소 → Settings → Secrets and variables → Actions → **New repository secret** 에서
   `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 3개를 등록
4. 끝. `.github/workflows/daily.yml` 이 매일 한국시간 오전 7시에 자동 실행됩니다.
   (시간 변경: yml 의 `cron` 값 수정, UTC 기준 / Actions 탭에서 "Run workflow"로 수동 테스트 가능)

### 방법 B — 내 PC에서 예약 (PC가 켜져 있어야 함)
- **Mac/Linux (cron):**
  ```bash
  crontab -e
  # 매일 오전 7시:
  0 7 * * * cd /경로/news_bot && /usr/bin/python3 main.py
  ```
- **Windows:** 작업 스케줄러 → 매일 → 프로그램 `python`, 인수 `main.py`

---

## 폴더 구조
```
news_bot/
├── .env.example         # 키 입력 양식 (복사해서 .env 로)
├── config.py            # 설정 + 관심 주제
├── main.py              # ▶ 실행 파일
├── get_chat_id.py       # chat_id 확인 도우미
├── summarizer.py        # 논문 요약
├── telegram_sender.py   # 텔레그램 전송
├── sources/
│   ├── web_research.py  # Google News RSS 뉴스 수집 + Gemini 정리
│   └── arxiv_papers.py  # 논문 수집
└── .github/workflows/daily.yml  # 자동 실행 설정
```

## 참고
- 뉴스는 Google News RSS(무료, 키 불필요)로 수집한 뒤 Gemini가 중복 제거·요약을 해줍니다.
- Gemini 무료 티어는 분당/일일 호출 횟수 제한이 있습니다. 지금 구조(주제 3개 + 논문 요약, 하루 1번 실행)는
  무료 한도 안에서 충분히 여유 있게 동작합니다. 주제를 아주 많이 늘리면 한도에 걸릴 수 있으니 유의하세요.
- 완전 무료 구성: GitHub Actions(무료) + Gemini API(무료 티어) + Google News RSS(무료) + arXiv(무료) + 텔레그램(무료).
  결제수단 등록이 필요한 곳이 없습니다.

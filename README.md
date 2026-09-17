# 📡 AI 기회정보 & 핵심 브리핑 봇

국내 AI 대회·공모전·해커톤·교육/지원사업과 꼭 볼 만한 AI 뉴스/논문을 정리해서
**텔레그램**으로 보내줍니다.
LLM은 OpenAI 호환 게이트웨이(`chat/completions` 스펙을 따르는 곳이면 어디든) + Google News RSS + arXiv +
텔레그램 + GitHub Actions 조합으로 동작합니다.

---

## 필요한 것 3가지 (전부 `.env` 한 곳에만 입력)

| 항목 | 발급처 |
|------|--------|
| `LLM_API_KEY` | 사용할 OpenAI 호환 LLM 게이트웨이/서비스에서 발급 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램에서 `@BotFather` → `/newbot` |
| `TELEGRAM_CHAT_ID` | 아래 3-2단계에서 자동 확인 |

기본 게이트웨이 주소/모델은 `config.py`에 이미 설정되어 있고, 다른 걸 쓰고 싶으면 `.env`에
`LLM_BASE_URL`, `LLM_MODEL`을 추가로 넣어 덮어쓸 수 있습니다.

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

### 4. LLM API 키 입력
1. 사용할 OpenAI 호환 게이트웨이/서비스에서 API 키 발급
2. 발급받은 키를 `.env` 의 `LLM_API_KEY` 에 붙여넣기

### 5. 실행
```bash
python main.py
```
텔레그램에 브리핑이 도착하면 성공입니다. 🎉

---

## 관심 주제 바꾸기
`config.py`의 `REQUESTED_INFO_TOPICS`에는 국내 모집 정보, `TOPICS`에는 핵심 뉴스 관심사를 넣습니다.
새로 받고 싶은 대회나 지원사업 종류는 `REQUESTED_INFO_TOPICS`에 같은 형식으로 추가하면 됩니다.
```python
REQUESTED_INFO_TOPICS = [
    {"label": "로봇 경진대회", "queries": ["국내 로봇 경진대회 참가자 모집"]},
]
ARXIV_CATEGORIES = ["cs.AI", "cs.CV"]   # cs.CL, stat.ML 등
ARXIV_KEYWORDS = ["large language model", "LLM", "RAG", ...]  # 초록에 포함될 키워드
```

---

## 실시간으로 받기

`live_monitor.py`는 기본 1분마다 새 정보를 확인하고, 새 후보가 있을 때만 LLM 요약과 텔레그램 전송을
실행합니다. PC가 켜져 있는 동안 계속 동작합니다.

```bash
python live_monitor.py
```

한 번만 확인하려면 `python live_monitor.py --once`를 사용합니다. 확인 간격은 `.env`의
`LIVE_POLL_INTERVAL_MINUTES`로 바꿀 수 있습니다. Windows에서는 `run_live.bat`로 실행할 수 있으며,
로그는 `live_monitor.log`에 기록됩니다.

기존 검색 결과를 발송하지 않고 지금 이후에 올라오는 항목만 받고 싶다면 최초 실행 전에
`python live_monitor.py --prime`으로 현재 후보를 기준선에 등록합니다.

## 전체 브리핑 수동 실행

### GitHub Actions
1. GitHub에서 새 저장소를 만듭니다 (Public/Private 무관, README 없이 빈 저장소로).
2. 로컬 저장소를 연결하고 올립니다. (`.env` 는 올라가지 않습니다 — `.gitignore` 처리됨)
   ```bash
   git remote add origin https://github.com/<내계정>/<저장소이름>.git
   git branch -M main
   git push -u origin main
   ```
3. 저장소 → Settings → Secrets and variables → Actions → **New repository secret** 에서
   `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 3개를 등록
   (게이트웨이 주소/모델을 기본값과 다르게 쓰려면 `LLM_BASE_URL`, `LLM_MODEL` 도 추가로 등록하고
   daily.yml/watchdog.yml의 env에도 추가해야 합니다.)
4. Actions 탭의 `manual-brief`에서 필요할 때 수동 실행합니다. 고정 시각 자동 실행은 비활성화되어 있습니다.

실시간 모니터는 Windows 로그인 시 자동 시작하도록 작업 스케줄러에 등록할 수 있습니다.

---

## 폴더 구조
```
news_bot/
├── .env.example              # 키 입력 양식 (복사해서 .env 로)
├── config.py                 # 설정 + 관심 주제 (+ KST 날짜 헬퍼)
├── main.py                   # ▶ 실행 파일
├── live_monitor.py           # 1분 간격 실시간 확인 및 새 항목 전송
├── run_live.bat              # Windows 실시간 모니터 실행
├── watchdog.py               # 수동 상태 점검
├── get_chat_id.py            # chat_id 확인 도우미
├── highlights.py             # 오늘의 Top 3 하이라이트 선정
├── llm_client.py             # LLM 호출 공용 로직 (재시도 포함, OpenAI 호환 게이트웨이)
├── summarizer.py             # 논문 요약
├── telegram_sender.py        # 텔레그램 전송
├── sources/
│   ├── web_research.py       # Google News + HN + 신뢰 매체 RSS 뉴스 수집 + LLM 정리
│   ├── korea_opportunities.py # 국내 AI 대회/공모전/모집 검색 + 원문/신청 링크 추출
│   ├── outlet_feeds.py       # 신뢰 매체(TechCrunch 등) + Reddit RSS
│   ├── hacker_news.py        # Hacker News 수집
│   ├── papers.py             # 논문 소스 통합(arXiv+OpenAlex+Semantic Scholar)
│   ├── arxiv_papers.py / openalex.py / semantic_scholar.py  # 논문 개별 소스
│   └── github_trending.py    # 최근 생성 + 스타 많은 AI 오픈소스 레포
├── archive/                  # 과거 브리핑 날짜별 markdown 보관
├── sent_history.json         # 중복 전송 방지 이력
├── last_success.json         # 워치독이 참조하는 마지막 성공 시각
└── .github/workflows/
    ├── daily.yml              # 전체 브리핑 수동 실행
    └── watchdog.yml           # 상태 수동 점검
```

## 참고
- 국내 기회정보는 한국어 검색 RSS에서 후보를 찾고 원문과 신청 링크를 읽은 뒤, 마감된 행사·내부 행사·단순
  홍보 기사를 제외합니다. 원문에 없는 접수일/상금/참가 조건은 추측하지 않고 `확인 필요`로 표시합니다.
- 뉴스는 Google News RSS + Hacker News + 신뢰 매체/Reddit RSS에서 모은 전체 후보 중 핵심만 최대 5개 보냅니다.
- GitHub Search API로 최근 만들어지고 스타가 많은 AI 관련 오픈소스도 함께 소개합니다 (공식 트렌딩 API가 없어 근사치).
- 모든 뉴스/논문/오픈소스를 통틀어 가장 중요한 3개를 뽑는 "오늘의 Top 3" 섹션이 맨 위에 붙습니다.
- 전체 브리핑을 수동 실행하면 `archive/YYYY-MM-DD.md`로 저장됩니다.
- 실시간 모니터는 새 후보가 없으면 LLM을 호출하지 않습니다. 새 후보가 있을 때만 기회정보/핵심 뉴스 요약을 호출하므로
  사용하는 게이트웨이의 요금·크레딧 정책을 확인하세요.
- 무료로 유지되는 부분: GitHub Actions(무료) + Google News/Reddit RSS(무료) + arXiv(무료)
  + GitHub Search API(무료) + 텔레그램(무료). LLM 비용만 사용하는 게이트웨이 정책에 따릅니다.

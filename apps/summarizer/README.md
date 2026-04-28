# News Summarizer

뉴스 기사 원문을 LLM으로 구조화·평가·요약하는 파이프라인입니다.
현재 저장소 기준 canonical 실행 경로는 `run_pipeline.py`와 `evaluate.py`입니다.

## 현재 baseline 상태

2026-04-27 기준 최신 baseline 결과:
- Step 2: 50/50 정상 (100.0%)
- Step 3: 유효 점수 50/50
- Step 4: 글자수 통과 50/50, 위반율 0.0%
- Step 5: clean 50/50, suspicious 0/50

자세한 상태/로그:
- `docs/current-status.md`
- `docs/progress-log.md`
- `reports/summary.md`

## 파이프라인 구조

```text
뉴스 원문 (plain text)
  → Step 1: 스크래핑
  → Step 2: JSON 변환 (title, date, author, content)
  → Step 3: 중요도 평가 (0~100 절대 점수)
  → Step 4: 요약 생성 (headline 3종 + summary)
  → Step 5: 사실 검증
  → evaluate.py: 품질 평가 리포트
```

## 현재 실행 기준

- 공식 실행 Python: `python3.11`
- Step 2/3 기본 경로: Hermit gateway (`http://localhost:8765/v1/chat/completions`)
- Hermit 기본 모델/프로바이더: `glm-5.1` / `z.ai`
- Step 4/5 baseline 경로: `codex exec`
- Step 4/5 baseline 모델: `gpt-5.4-mini`
- reasoning effort: `low`

중요:
- 시스템 `python3`는 3.9 계열일 수 있으므로 사용하지 말고 `python3.11`를 사용합니다.
- 과거 Ollama 기준 문서/스크립트는 대부분 정리됐지만, 실행 전에는 항상 `docs/current-status.md`를 우선 확인하세요.

## 실행 방법

전체 또는 step 단위 실행:

```bash
python3.11 run_pipeline.py
python3.11 run_pipeline.py --step 2
python3.11 run_pipeline.py --step 4
python3.11 run_pipeline.py --from 3
python3.11 evaluate.py
```

## Step 4/5 baseline 실행 예시

요약 생성:

```bash
PIPELINE_LLM_BACKEND=codex_exec \
PIPELINE_MODEL=gpt-5.4-mini \
PIPELINE_CODEX_REASONING_EFFORT=low \
PYTHONUNBUFFERED=1 \
python3.11 run_pipeline.py --step 4
```

사실 검증:

```bash
PIPELINE_LLM_BACKEND=codex_exec \
PIPELINE_MODEL=gpt-5.4-mini \
PIPELINE_CODEX_REASONING_EFFORT=low \
PYTHONUNBUFFERED=1 \
python3.11 run_pipeline.py --step 5
```

## 단건 테스트

`test_summarize.py`는 현재 Ollama 전용이 아니라 현행 Hermit/Codex 기준 단건 테스트 도구입니다.

파일 입력 기준:

```bash
python3.11 test_summarize.py --file data/json/009.json
python3.11 test_summarize.py --file data/json/009.json --verify
```

URL 입력 기준:

```bash
python3.11 test_summarize.py --url https://www.yna.co.kr/view/AKR20260424165300504
python3.11 test_summarize.py --url https://www.yna.co.kr/view/AKR20260424165300504 --verify
```

Hermit gateway 모델로 확인하고 싶다면:

```bash
python3.11 test_summarize.py --file data/json/009.json --backend hermit_http --model glm-5.1
```

주의:
- `--url` 모드는 `beautifulsoup4`가 필요합니다.
- 없으면 다음으로 설치합니다:

```bash
python3.11 -m pip install beautifulsoup4
```

## 요약 출력 스펙

```json
{
  "headline_34": "34자 이하 헤드라인",
  "headline_58": "58자 이하 헤드라인",
  "headline_89": "89자 이하 헤드라인",
  "summary": "2~3문장 본문 요약 (80~180자 권장)"
}
```

헤드라인 길이 기준:

| 필드 | 최소 | 최대 | 목표 |
|---|---:|---:|---:|
| `headline_34` | 29 | 34 | 32자 근처 |
| `headline_58` | 50 | 58 | 55자 근처 |
| `headline_89` | 76 | 89 | 83자 근처 |

## 파일 구조

```text
news_summurizer/
├── README.md
├── PRD.md
├── news_schema.py
├── news_service.py
├── news_adapter.py
├── run_pipeline.py
├── evaluate.py
├── test_summarize.py
├── docs/
│   ├── current-status.md
│   ├── pipeline-status.md
│   ├── progress-log.md
│   └── baseline-retest-plan.md
├── prompts/
│   ├── summarizer_system.md
│   └── user_prompt_template.md
├── pipeline/
│   ├── common.py
│   ├── step1_scrape.py
│   ├── step2_to_json.py
│   ├── step3_score.py
│   ├── step4_summarize.py
│   └── step5_verify.py
├── data/
│   ├── raw/
│   ├── json/
│   ├── scored/
│   ├── summarized/
│   ├── verified/
│   └── _baseline_backups/
└── reports/
```

## 백엔드 연동용 요약 라이브러리

현재 권장 통합 방식은 HTTP API가 아니라 라이브러리 import 입니다.
메인 백엔드 서버가 `news_service.py`의 `NewsSummarizer`를 직접 호출하거나,
`news_adapter.py`의 adapter 함수를 통해 요청/응답 스키마를 고정해서 사용할 수 있습니다.

핵심 파일:
- `news_schema.py` — Pydantic 입력/출력 스키마
- `news_service.py` — 실제 요약 라이브러리
- `news_adapter.py` — 백엔드 요청 플로우용 adapter 함수

Pydantic 스키마 + adapter 예시:

```python
from news_adapter import summarize_request
from news_schema import NewsArticle, SummarizeRequest, SummarizerSettings

request = SummarizeRequest(
    article=NewsArticle(
        title="기사 제목",
        date="2026-04-27",
        author="기자명",
        content="기사 본문",
    ),
    verify=True,
    max_retries=2,
)

settings = SummarizerSettings(
    backend="codex_exec",
    model="gpt-5.4-mini",
    reasoning_effort="low",
    timeout=300,
)

result = summarize_request(request, settings)
print(result.model_dump(by_alias=True))
```

직접 라이브러리 호출 예시:

```python
from news_service import NewsSummarizer

summarizer = NewsSummarizer(
    backend="codex_exec",
    model="gpt-5.4-mini",
    reasoning_effort="low",
)

article = {
    "title": "기사 제목",
    "date": "2026-04-27",
    "author": "기자명",
    "content": "기사 본문"
}

result = summarizer.summarize(article, verify=True)
```

지원 기능:
- `NewsSummarizer.summarize(article, verify=False)`
- `NewsSummarizer.summarize_model(article_model, verify=False)`
- `NewsSummarizer.summarize_file(path, verify=False)`
- `NewsSummarizer.summarize_url(url, verify=False)`
- `summarize_request(request, settings)`

입력은 기사 1건, 출력은 요약 1건입니다.
이 라이브러리는 데이터 저장, 목록 조회, 카테고리 피드 조립을 담당하지 않습니다.

## 참고 문서

- `PRD.md` — 요구사항 + 설계 결정 + 최종 baseline 결과
- `docs/current-status.md` — 현재 실행 기준 요약
- `docs/progress-log.md` — 실제 실행/수정 로그
- `reports/summary.md` — 최신 평가 리포트

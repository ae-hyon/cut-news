# 뉴스 요약 서비스 PRD

> 최종 수정: 2026-04-27
> 참고: 이 문서는 요구사항 + 현재까지의 실험/결정 이력을 함께 담는 문서입니다. 현재 실행 상태와 진행 로그는 `docs/current-status.md`, `docs/pipeline-status.md`, `docs/progress-log.md`, `docs/baseline-retest-plan.md`를 우선 참고하세요.

---

## 1. 서비스 개요

뉴스 기사 원문을 LLM으로 구조화·평가·요약하여 사용자에게 제공하는 서비스.
크롤러/수집 단계에서 확보한 원문을 받아 다음 파이프라인으로 처리한다.

- raw text 수집
- JSON 구조화
- 중요도 절대평가(0~100)
- headline 3종 + summary 생성
- 사실 검증

---

## 2. 화면 모드

### 2-1. 넓게보기
- 대분류(경제 / 연예 / 사회 / ...) 목록 표시
- 각 대분류에서 대표 기사 5개 요약 표시
- 한 화면에 최대 5개

### 2-2. 깊게보기
- 대분류 선택 → 중분류 선택 (예: 경제 → 금융)
- 선택한 중분류에서 대표 기사 5개 표시
- 중분류 기사가 5개 미만이면 나머지를 대분류(부모)에서 채움

```text
넓게보기: [대분류] → 대분류 기사 5개
깊게보기: [대분류] → [중분류] → 중분류 기사 (n개) + 대분류 기사 (5-n개)
```

---

## 3. 카테고리 구조 (예시)

```text
대분류
├── 경제
│   ├── 금융
│   ├── 부동산
│   ├── 미국 경제
│   └── ...
├── 사회
│   ├── 교육
│   ├── 환경
│   └── ...
└── 연예
    ├── 음악
    ├── 드라마
    └── ...
```

---

## 4. 기사 데이터 흐름

```text
크롤링/수집
  └─ 뉴스 URL + 원문(제목/날짜/기자/본문) 수집
       │
       ▼
[Step 2] raw text → JSON 구조화
       │
       ▼
[Step 3] 중요도 점수 할당 (절대평가 0~100)
       │
       ▼
[Step 4] headline_34 / headline_58 / headline_89 / summary 생성
       │
       ▼
[Step 5] 사실 검증 (hallucination check)
       │
       ▼
서비스 응답 / 리포트 생성
```

주의:
- 현재 저장소 기준 실행 순서는 `run_pipeline.py`의 Step 1~5 정의를 따른다.
- 실제 baseline 재테스트에서는 Step 2~5와 `evaluate.py`를 기준으로 품질을 확인했다.

---

## 5. 입출력 스펙

### 입력 (LLM에 전달하는 기사 JSON)
```json
{
  "title": "원본 기사 제목",
  "date": "YYYY-MM-DD",
  "author": "기자명",
  "content": "기사 본문 plain text"
}
```

### 출력 (요약 결과 JSON)
```json
{
  "headline_34": "34자 이하 헤드라인",
  "headline_58": "58자 이하 헤드라인",
  "headline_89": "89자 이하 헤드라인",
  "summary": "2~3문장 요약"
}
```

### 검증 결과 JSON
```json
{
  "verdict": "clean 또는 suspicious",
  "hallucinations": ["원문에 없는 내용1", "원문에 없는 내용2"],
  "confidence": 0
}
```

---

## 6. 현재 기술 스택 / 실행 기준

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.11 |
| HTTP 라이브러리 | requests |
| HTML 파싱 | BeautifulSoup4 |
| 파이프라인 실행 | `run_pipeline.py` |
| 평가 리포트 | `evaluate.py` |
| Hermit gateway | `http://localhost:8765/v1/chat/completions` |
| Hermit 기본 모델 | `glm-5.1` |
| Hermit provider | `z.ai` |
| 요약/검증 baseline 모델 | `gpt-5.4-mini` |
| 요약/검증 baseline backend | `codex exec` |
| reasoning effort | `low` |

중요 실행 원칙:
- 시스템 `python3`가 아니라 반드시 `python3.11` 사용
- Step 2/3은 Hermit gateway(`glm-5.1` + z.ai) 기준으로 동작
- Step 4/5 baseline은 `codex_exec` + `gpt-5.4-mini` + `low` 기준으로 검증 완료

---

## 7. 파일 구조

```text
news_summurizer/
├── PRD.md
├── README.md
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
└── data/
    ├── raw/
    ├── json/
    ├── scored/
    ├── summarized/
    ├── verified/
    └── _baseline_backups/
```

---

## 8. 핵심 설계 결정

### 8-1. 중요도 평가는 절대평가 방식 사용

- 사용자마다 구독 카테고리가 다름
- 정치 기사가 90점, 연예 기사가 30점이라도 연예만 구독한 유저에게는 연예 30점 기사가 노출될 수 있음
- 따라서 카테고리 간 상대 순위보다 기사 자체의 절대적 가치(0~100)를 독립 평가하는 방식이 적합

```text
❌ 상대 평가: 이번 배치에서 가장 중요한 기사 순위
✅ 절대 평가: 이 기사 자체가 독자에게 얼마나 가치 있는가 (0~100)
```

### 8-2. Step 2는 LLM-only보다 fallback 복구가 필요

baseline 재테스트에서 확인된 문제:
- gateway가 HTTP 200 + error body를 반환하는 경우 존재
- rate limit 반복 발생
- 일부 기사에서 장시간 timeout 발생

따라서 현재 Step 2에는 다음 보강이 들어가 있다.
- 재시도 + 지수 백오프
- 연합뉴스 형식 원문 fallback 파서
- 날짜 줄 종료 조건 보정 (`2024년 ...` 같은 본문 문장을 잘못 끊지 않도록 수정)

### 8-3. 요약 단계는 속도/비용/안정성 우선

기존 z.ai/glm 경로는 느리고 불안정한 구간이 있었고, 사용자는 더 가벼운 GPT 계열 경로를 허용했다.
현재 baseline 기준:
- Step 4/5는 `codex exec` 경유
- 모델은 `gpt-5.4-mini`
- reasoning effort는 `low`

### 8-4. 요약 프롬프트 보강 규칙

최종적으로 품질을 100% clean까지 끌어올리기 위해 다음 규칙을 추가했다.
- 원문에 없는 해석/배경 추론 금지
- 기상 기사에 상식적 주의 문구 임의 추가 금지
- 인사 기사에 `재편`, `정비`, `마무리` 같은 해석 표현 금지
- headline 길이 위반 시 피드백 포함 자동 재생성

---

## 9. baseline 재테스트 결과 (2026-04-27 최종)

### 전체 산출물 상태
- `data/json/`: 50 정상 / 0 error
- `data/scored/`: 50 정상 / 0 error
- `data/summarized/`: 50 정상 / 0 error
- `data/verified/`: 50 정상 / 0 error

### 최종 평가 요약

| 단계 | 최종 결과 |
|---|---|
| Step 2 (JSON 변환) | 50/50 정상 (100.0%) |
| Step 3 (중요도) | 유효 점수 50/50 |
| Step 4 (요약) | 글자수 통과 50/50, 위반율 0.0% |
| Step 5 (검증) | clean 50/50, suspicious 0/50 |

### 세부 수치
- Step 2 평균 본문 길이: 850자
- Step 3 평균 점수: 67.1 (min 25 / max 98)
- Step 4 평균 headline 길이: h34=31.1자 / h58=52.7자 / h89=81.0자
- Step 4 평균 summary 길이: 119.4자

---

## 10. 이번 baseline에서 해결한 주요 이슈

1. Step 2 timeout / gateway error / rate limit
- timeout 상향
- error body 재시도
- fallback parser 도입

2. Step 2 본문 조기 종료 버그
- `038.json`에서 본문 중 `2024년 ...` 문장이 날짜 줄로 잘못 인식되는 문제 수정

3. Step 3 리포트 왜곡
- stale error 파일(`data/scored/004_error.json`) 제거 후 재평가

4. Step 4 headline 길이 위반
- `009`, `034` 재생성으로 해소
- 자동 길이 retry 로직 추가

5. Step 5 hallucination suspicious
- `040`, `047`에서 원문 없는 문구 제거
- prompt 규칙 보강 후 clean으로 정리

6. 디스크 공간 부족
- baseline 중 여러 차례 `No space left on device` 발생
- `~/.cache` 및 temp 정리로 작업 지속

---

## 11. test_summarize.py 현재 역할

`test_summarize.py`는 더 이상 Ollama 전용 스크립트가 아니다.
현재는 다음 용도로 사용한다.
- URL 1건 요약 테스트
- `data/json/*.json` 단건 요약 테스트
- 필요 시 사실 검증까지 함께 실행

기본 실행 예시:
```bash
python3.11 test_summarize.py --url https://www.yna.co.kr/view/AKR20260424165300504
python3.11 test_summarize.py --file data/json/009.json --verify
```

기본값:
- backend: `codex_exec`
- model: `gpt-5.4-mini`
- reasoning effort: `low`

Hermit gateway로 확인하고 싶다면:
```bash
python3.11 test_summarize.py --file data/json/009.json --backend hermit_http --model glm-5.1
```

---

## 12. 남은 작업 / 후속 제안

- [x] `test_summarize.py` 사용법을 README에도 반영
- [ ] 필요 시 prompt 개선 내용을 별도 문서/체크리스트로 추출
- [x] 백엔드 import용 순수 요약 라이브러리 구현 (`news_service.py`)
- [x] `test_summarize.py`를 라이브러리 thin wrapper로 정리
- [x] 입력/출력 스키마를 Pydantic으로 고정 (`news_schema.py`)
- [x] 백엔드 요청 플로우용 adapter 추가 (`news_adapter.py`)
- [ ] 메인 백엔드 서버 요청 플로우에 `summarize_request(...)` 또는 `NewsSummarizer` 연결

참고:
- 디스크 부족 cleanup 가이드 문서화는 사용자 요청으로 진행하지 않음
- 카테고리/피드 조립은 현재 핵심 범위가 아니며, 이 컴포넌트의 책임은 요약 생성에 한정함

---

## 13. 참고 문서

- `docs/current-status.md` — 현재 실행 기준과 최신 결과 요약
- `docs/progress-log.md` — 실제 실행/수정 이력
- `docs/pipeline-status.md` — 운영 기준 메모
- `docs/baseline-retest-plan.md` — baseline 재테스트 계획
- `reports/summary.md` — 최신 평가 리포트

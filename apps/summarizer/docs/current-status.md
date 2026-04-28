# 뉴스 요약 프로젝트 현재 상태

최종 갱신: 2026-04-28 01:46:10 KST

## 현재 실행 기준
- 공식 실행 Python: `python3.11`
- 구조화/점수 기본 경로: `run_pipeline.py` + `pipeline/common.py`
- Hermit gateway endpoint: `http://localhost:8765/v1/chat/completions`
- Hermit 기본 모델/프로바이더: `glm-5.1` / `z.ai`
- 요약/검증 우회 경로: `codex exec`
- 현재 요약/검증 기준 모델: `gpt-5.4-mini`
- reasoning effort: `low`

## 현재 산출물 상태
- `data/raw/`: 50개
- `data/json/`: 50개 정상 / 0개 error
- `data/scored/`: 50개 정상 / 0개 error
- `data/summarized/`: 50개 정상 / 0개 error
- `data/verified/`: 50개 정상 / 0개 error
- `reports/summary.md` 및 step별 리포트 최신 기준으로 재생성 완료
- 길이 비교 리포트 추가:
  - `reports/length_distribution_before_tuning.json`
  - `reports/length_distribution_after_tuning.json`

## 최신 평가 결과
- Step 2: 50/50 정상 (100.0%)
- Step 3: 유효 점수 50/50
- Step 4: 글자수 통과 50/50, 위반율 0.0%
- Step 5: clean 50/50, suspicious 0/50

## 이번 길이 튜닝 결과
### 기준
- `headline_34`: 29~34자
- `headline_58`: 50~58자
- `headline_89`: 76~89자

### 수정 전 → 수정 후 분포
- h34
  - 평균: 31.06 → 32.88
  - 최소: 28 → 29
  - 목표값 34 정확히 일치: 7건 → 18건
  - 목표값 ±2 이내: 16건 → 47건
  - 목표값 ±4 이내: 40건 → 49건
- h58
  - 평균: 52.74 → 55.62
  - 최소: 45 → 51
  - 목표값 58 정확히 일치: 1건 → 9건
  - 목표값 ±2 이내: 7건 → 25건
  - 목표값 ±4 이내: 23건 → 47건
- h89
  - 평균: 80.98 → 84.74
  - 최소: 65 → 78
  - 목표값 89 정확히 일치: 2건 → 2건
  - 목표값 ±2 이내: 5건 → 15건
  - 목표값 ±4 이내: 14건 → 25건
- 최종 길이 위반 건수: 0건

## 이번에 반영된 품질/운영 개선
1. `news_schema.py`
- headline 길이 검증을 최대값 기준에서 범위 기준으로 강화
- headline 문자열 공백 정규화 후 길이 검증

2. `news_service.py`
- 초기 prompt에 "상한 근처까지 채우기" 지시 추가
- too short / too long 구분 길이 재시도 prompt 추가
- 범위는 맞지만 너무 짧은 경우 densify retry 추가
- 결과 문자열 정규화 후 길이 측정/검증하도록 변경

3. `pipeline/step4_summarize.py`
- 라이브러리와 같은 길이 범위/밀도 기준으로 동기화
- too short / too long 재시도 로직 반영
- 결과 문자열 정규화 반영

4. `core-backend/app/presentation/schemas.py`
- summary 응답 길이 계약을 backend에서도 동일하게 검증
- 계약 위반 시 표준 에러 응답으로 막을 수 있는 기반 유지

## 주의 사항
- 시스템 `python3`는 3.9 계열이라 공식 실행에 사용하면 안 됨
- URL 입력 모드(`--url`)는 `beautifulsoup4`가 필요함. 없으면 `python3.11 -m pip install beautifulsoup4` 후 실행
- 디스크 여유 공간이 다시 바닥나기 쉬움. 대량 재생성 전 `~/.cache`와 temp 사용량 확인 권장
- `run_pipeline.py --step 5`는 이미 존재하는 `data/verified/*.json`을 스킵하면서 콘솔에 실패처럼 보일 수 있으나, 실제 평가는 `evaluate.py` 기준 리포트를 확인해야 함

## 이번에 추가된 백엔드 연동 계층
- `news_schema.py` 추가
- `news_service.py` 추가
- `news_adapter.py` 추가
- `NewsArticle`, `SummarizeRequest`, `SummaryResult`, `SummarizerSettings` 등 Pydantic 스키마 제공
- `NewsSummarizer` 클래스로 기사 1건 -> 요약 1건 처리 가능
- `summarize_request(...)` adapter 함수로 백엔드 요청 플로우에 바로 연결 가능
- 저장/조회 없이 순수 요약 기능만 제공
- `test_summarize.py`는 이 라이브러리를 호출하는 thin wrapper로 정리

## 다음 작업 추천
1. 메인 백엔드 서버에서 `summarize_request(...)` 또는 `NewsSummarizer`를 실제 요청 플로우에 연결
2. 필요하면 Step 4 `_error.json`을 길이 계약 위반/LLM 호출 실패 등 유형별로 더 구조화
3. `length_distribution_before_tuning.json` / `after_tuning.json`과 `evaluate.py` 리포트를 같은 계산 경로로 통합해 중복 집계를 줄이기

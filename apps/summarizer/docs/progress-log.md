# 진행 로그

이 문서는 실제로 확인한 사실과 수행한 작업만 시간순으로 기록한다.

## 2026-04-27

### 15:52 KST — 현재 상태 재정리 시작
확인 사항:
- 프로젝트 실제 경로: `/Users/reddit/Project/school/web-programming/news_summurizer`
- 현재 저장소는 git repo가 아님
- 실제 LLM 호출 경로는 `pipeline/common.py` 기준 Hermit gateway
- endpoint: `http://localhost:8765/v1/chat/completions`
- model: `glm-5.1`
- `~/.hermit/settings.json`에서 Hermit 기본 모델과 z.ai provider 설정 확인

### 15:53 KST — 과거 문서와 현재 코드의 기준 불일치 확인
확인 사항:
- `docs/pipeline-status.md`는 Ollama / gemma 기준 기록
- `test_summarize.py`도 Ollama 전용 스크립트
- 반면 파이프라인 본체는 Hermit gateway 기반

판단:
- baseline 재테스트는 `run_pipeline.py` 중심으로 다시 잡아야 함
- `test_summarize.py`는 현 시점에서 보조/구버전 도구로 간주

### 15:54 KST — 산출물 불일치 확인
확인 사항:
- `data/raw/` 50개 존재
- `data/json/` 일부만 존재
- `data/scored/`, `data/summarized/`, `data/verified/` 비어 있음
- `reports/summary.md`에는 과거 50건 완료 기록 존재
- `data/summarized_backup_v1/`에는 과거 요약 50건 백업 존재

판단:
- 예전에는 50건 end-to-end 실행 완료
- 현재는 중간 상태로 돌아간 작업 트리
- 따라서 baseline 재구성이 우선

### 15:55 KST — 재실행 blocker 확인
실행:
- `python3 run_pipeline.py --step 2`

결과:
- 실패
- 원인: 시스템 `python3`는 3.9.0이며 `dict | None` 타입 문법을 지원하지 않음

판단:
- 파이프라인 공식 실행 버전은 `python3.11`

### 15:56 KST — Hermit gateway 최소 호출 성공 확인
실행:
- Hermit gateway에 최소 chat completion 요청 전송

결과:
- `glm-5.1` 응답 성공
- gateway는 현재 사용 가능

판단:
- 현재 문제는 모델 연결이 아니라 실행 기준/테스트 기준 정리 문제에 가까움

## 다음 기록 규칙
- 실제 실행한 명령만 적는다.
- 추정은 `판단:` 아래에만 적는다.
- 재테스트 시작 시 step별 결과를 이 문서에 계속 누적한다.

### 16:53 KST — baseline 재테스트 시작
실행:
- 기존 `data/json`, `data/scored`, `data/summarized`, `data/verified`, `reports`를 `data/_baseline_backups/<timestamp>/` 아래로 이동
- 새 출력 디렉터리 재생성
- `python3.11 run_pipeline.py --step 2` 시작

결과:
- Step 2는 120초 timeout 기준에서 1건 생성 후 장시간 정체
- 단일 기사 재현 결과, `glm-5.1` 기준 변환 요청이 120초를 넘기는 사례 확인

판단:
- Step 2~5의 LLM timeout을 현 gateway/model 현실에 맞게 상향할 필요가 있음

### 16:53 KST — 재실행 중 발견한 blocker 수정
실행:
- `pipeline/step2_to_json.py`, `pipeline/step3_score.py`, `pipeline/step4_summarize.py`, `pipeline/step5_verify.py`에 `PIPELINE_MAX_WORKERS` 기반 병렬 실행 옵션 추가
- `pipeline/common.py`의 LLM 공통 호출부를 수정해 HTTP 200 + `{\"error\": ...}` 본문을 재시도 대상으로 처리
- `~/.cache` 정리 및 중간 `_error.json` 삭제로 디스크 공간 확보

결과:
- 기존 실패 원인 2개 확인:
  - gateway/provider가 HTTP 200 본문에 `error` 객체를 반환하는 경우가 있었음
  - 디스크 공간 부족으로 `No space left on device` 발생
- 정리 후 사용 가능 공간 약 2.3GiB 확보
- 단일 기사 `006`, `007`은 수정 후 정상 통과 확인

판단:
- 현재 baseline blocker는 해소된 상태
- 병렬도는 gateway 안정성과 속도 균형을 보며 조정 필요

### 16:53 KST — Step 2 재실행 진행 중
실행:
- `PIPELINE_MAX_WORKERS=4 PYTHONUNBUFFERED=1 python3.11 run_pipeline.py --step 2`
- 실패/누락 건은 이후 규칙 기반 fallback 파서를 추가해 보정

중간 결과:
- 초기 진행 구간에서는 worker 4 기준으로 순차/worker 2보다 빠르게 전진
- 이후 gateway/provider 측 rate limit(`Rate limit reached for requests`)이 반복 발생
- 일부 기사는 safety 차단, JSON 파싱 실패, 재시도 초과로 누락 발생

최종 결과:
- `data/json/` 50개 전체 생성 완료
- 누락되던 `003`, `029`, `038`, `039`는 연합뉴스 형식 fallback 파서로 복구
- `020`은 재시도로 정상 복구
- `pipeline/step2_to_json.py`에 fallback 파싱과 집계 개선 추가

판단:
- 현재 Step 2는 z.ai 안정성과 무관하게 재현 가능한 상태로 정리됨
- 구조화 단계는 LLM 의존도를 더 낮출 수 있는 방향이 맞음

### 17:18 KST — 요약 경로를 Codex mini로 전환
실행:
- `pipeline/common.py`에 `codex exec` 기반 백엔드(`PIPELINE_LLM_BACKEND=codex_exec`) 추가
- 모델/effort를 환경변수로 제어 가능하게 변경
- `pipeline/step4_summarize.py`에 `PIPELINE_SKIP_INLINE_VERIFY=1` 옵션 추가
- 단건 검증: `gpt-5.4-mini` + `low` effort로 기사 1건 요약 성공 확인

결과:
- Hermit HTTP `/v1/chat/completions` 경로는 `gpt-5.4`/`gpt-5.4-mini`를 직접 라우팅하지 못함 확인
- 대신 Codex CLI 비대화형 실행으로 GPT 요약 경로 확보
- 현재 Step 4 배치 시작:
  - `PIPELINE_LLM_BACKEND=codex_exec`
  - `PIPELINE_MODEL=gpt-5.4-mini`
  - `PIPELINE_CODEX_REASONING_EFFORT=low`
  - `PIPELINE_SKIP_INLINE_VERIFY=1`
  - 프로세스: `proc_e987aacdd1c6`

판단:
- 사용자의 "z.ai 대신 가벼운 GPT로 요약" 요청은 현재 이 경로가 가장 현실적
- Step 4 완료 후 품질/속도를 보고 Step 3·5 재실행 방식도 다시 정리할 예정

### 18:34 KST — baseline 재테스트 완료
실행:
- Step 4 완료 확인: `PIPELINE_LLM_BACKEND=codex_exec PIPELINE_MODEL=gpt-5.4-mini PIPELINE_CODEX_REASONING_EFFORT=low PIPELINE_SKIP_INLINE_VERIFY=1 PIPELINE_MAX_WORKERS=1 PYTHONUNBUFFERED=1 python3.11 run_pipeline.py --step 4`
- Step 3 실행: `PIPELINE_MAX_WORKERS=4 PYTHONUNBUFFERED=1 python3.11 run_pipeline.py --step 3`
- Step 3 잔여 5건 보완 실행: `PIPELINE_MAX_WORKERS=1 PYTHONUNBUFFERED=1 python3.11 run_pipeline.py --step 3`
- Step 5 실행: `PIPELINE_LLM_BACKEND=codex_exec PIPELINE_MODEL=gpt-5.4-mini PIPELINE_CODEX_REASONING_EFFORT=low PIPELINE_SKIP_INLINE_VERIFY=1 PIPELINE_MAX_WORKERS=1 PYTHONUNBUFFERED=1 python3.11 run_pipeline.py --step 5`
- 평가 리포트 생성: `python3.11 evaluate.py`

중간 이슈:
- Step 3 첫 실행은 z.ai gateway rate limit 때문에 600초 timeout 안에 45건만 완료
- `data/scored/004_error.json`이 남아 Step 3 리포트 집계를 51건으로 왜곡
- Step 2의 `038.json`은 fallback 파서가 본문 중 `2024년 ...` 문장에서 조기 종료되어 content 길이가 비정상적으로 짧았음

수정:
- `pipeline/step2_to_json.py` fallback 파서의 날짜 줄 종료 조건을 `re.match(^20...)`에서 순수 timestamp 줄만 끊도록 좁힘
- `data/json/038.json` 재생성 후 content 길이 정상화
- stale error 파일 `data/scored/004_error.json` 제거
- `python3.11 evaluate.py` 재실행

최종 결과:
- `data/json/` 50개 정상 / 0개 error
- `data/scored/` 50개 정상 / 0개 error
- `data/summarized/` 50개 정상 / 0개 error
- `data/verified/` 50개 정상 / 0개 error
- Step 2: 50/50 정상 (100.0%)
- Step 3: 유효 점수 50/50
- Step 4: 글자수 통과 48/50, 위반 2건(`009`, `034`)
- Step 5: clean 48/50, suspicious 2건(`040`, `047`)

판단:
- baseline 재테스트는 완료 상태로 볼 수 있음
- 다음 최우선 작업은 전체 재실행이 아니라 품질 이슈 4건(`009`, `034`, `040`, `047`) 타겟 수정임

### 18:49 KST — 품질 이슈 4건 타겟 수정 완료
실행:
- `pipeline/step4_summarize.py`에 초기 요약 prompt 강화 로직 추가
- 기상 기사에 원문 없는 안전/주의 문구를 넣지 않도록 제약 추가
- 인사 기사에 원문 없는 해석 표현(`재편`, `정비`, `마무리`)을 넣지 않도록 제약 추가
- headline 길이 위반 시 피드백을 포함해 자동 재생성하는 retry 로직 추가
- 대상 4건(`009`, `034`, `040`, `047`)의 `data/summarized/*.json` 재생성
- 대상 4건의 `data/verified/*.json` 재검증
- `python3.11 evaluate.py` 재실행

중간 이슈:
- 047 재생성 중 디스크 부족으로 `No space left on device` 발생
- `~/.cache` 및 Hermes temp 일부 정리 후 재실행

최종 결과:
- `009`, `034`의 headline 길이 위반 해소
- `040`, `047`의 hallucination suspicious 해소
- Step 4: 글자수 통과 50/50, 위반율 0.0%
- Step 5: clean 50/50, suspicious 0/50

판단:
- 현재 baseline 결과는 길이/팩트 기준 모두 통과 상태
- 다음 작업은 전체 파이프라인 수정이 아니라 stale 테스트 스크립트와 PRD 정리 쪽이 우선

### 20:15 KST — 단건 테스트 스크립트와 PRD 최신화
실행:
- `test_summarize.py`를 Ollama 전용 스크립트에서 현행 Hermit/Codex 기준 단건 테스트 도구로 재작성
- 기본값을 `codex_exec` + `gpt-5.4-mini` + `low`로 설정
- `--url`, `--file`, `--verify`, `--backend`, `--model`, `--reasoning-effort` 옵션 추가
- `PRD.md`를 현재 baseline 기준으로 전면 갱신
- `python3.11 -m py_compile test_summarize.py` 실행
- `python3.11 test_summarize.py --file data/json/009.json --verify` 실행

중간 이슈:
- 실행 환경에 `bs4`가 없어 URL 크롤링 코드가 import 단계에서 실패
- `BeautifulSoup`를 URL 모드에서만 lazy import하도록 수정
- `--file` 입력 경로는 추가 설치 없이 정상 동작 확인

최종 결과:
- `test_summarize.py`는 현행 baseline 기준으로 실제 실행 검증 완료
- `PRD.md`에 최신 실행 기준, 설계 결정, baseline 최종 수치 반영 완료

판단:
- 현재 저장소의 stale 문서/테스트 혼선은 대부분 해소된 상태
- 다음 우선순위는 `README.md` 최신화와 서비스 로직 쪽 후속 작업 정리

### 20:16 KST — README 최신 실행 기준 반영
실행:
- `README.md`를 현재 baseline 기준으로 전면 갱신
- `python3.11` 실행 원칙, Hermit/Codex baseline 경로, Step 4/5 실행 예시, `test_summarize.py` 사용 예시 반영
- 디스크 정리 가이드는 사용자 요청으로 별도 문서화하지 않음

### 20:31 KST — 서비스 응답 조립 계층 추가
실행:
- `service_response.py` 추가
- 카테고리 메타데이터 템플릿 `data/category_map.template.json` 추가
- `docs/service-response.md` 작성
- `README.md`, `PRD.md`, `docs/current-status.md`에 새 응답 계층 반영
- 검증용 임시 카테고리 맵으로 `wide` / `deep` 모드 실행 확인 후 임시 파일 제거

결과:
- 현재 파이프라인 산출물과 별개로 실제 화면 모드용 응답 JSON을 만들 수 있는 계층이 생김
- `넓게보기`: 대분류별 상위 기사 최대 5개 반환 가능
- `깊게보기`: 중분류 기사 우선 + 부족분은 같은 대분류 기사로 보충 가능
- 이어서 실제 기사 50건용 `data/category_map.json` 초안도 작성 완료
- 남은 핵심 작업은 이 응답 계층을 실제 API/웹 계층에 연결하는 것

### 20:48 KST — 방향 수정: 순수 요약 라이브러리 우선
실행:
- 사용자 요청에 맞춰 저장/조회 중심이 아닌 순수 요약 라이브러리 방향으로 재정리
- `news_service.py`를 `NewsSummarizer` 중심 라이브러리로 작성
- 기사 dict 1건 입력 -> headline 3종 + summary 출력 구조로 정리
- 선택적으로 `verify=True` 시 사실 검증도 함께 수행 가능하게 구성
- `test_summarize.py`를 라이브러리 호출 thin wrapper로 재작성
- `python3.11 -m py_compile news_service.py test_summarize.py` 검증
- `python3.11 test_summarize.py --file data/json/009.json --verify` 실행 검증

결과:
- 메인 백엔드 서버는 HTTP/API 계층 없이 `NewsSummarizer`를 import 해서 바로 사용할 수 있게 됨
- 이 컴포넌트는 데이터 저장, 목록 조회, 카테고리 조립을 담당하지 않고 요약만 담당함
- 현재 권장 통합 방식은 라이브러리 호출

### 20:56 KST — Pydantic 스키마와 백엔드 adapter 추가
실행:
- `news_schema.py` 작성
- `NewsArticle`, `SummarizeRequest`, `SummaryResult`, `VerificationResult`, `SummarizerSettings` 스키마 추가
- `news_adapter.py` 작성
- `summarize_request(...)`, `build_summarizer(...)` 함수 추가
- `news_service.py`를 Pydantic 모델 기반 메서드(`summarize_model`, `verify_model`) 중심으로 확장
- `python3.11 -m py_compile news_schema.py news_adapter.py news_service.py test_summarize.py` 검증
- adapter 경유 실제 요약/검증 호출 실행 확인

결과:
- 백엔드 서버는 dict를 느슨하게 넘길 수도 있고, Pydantic request/response 모델로 엄격하게 붙일 수도 있게 됨
- 현재 가장 안정적인 통합면은 `SummarizeRequest` + `summarize_request(...)` 조합

최종 결과:
- 저장소의 핵심 진입 문서(`README.md`, `PRD.md`, `docs/current-status.md`)가 동일한 최신 실행 기준을 가리키도록 정리됨

### 01:24 KST — 길이 목표 근접도 튜닝 후 50건 전체 재실행
실행:
- 수정 전 길이 분포를 `reports/length_distribution_before_tuning.json`으로 저장
- `news_schema.py`, `news_service.py`, `pipeline/step4_summarize.py`, `core-backend/app/presentation/schemas.py`에 길이 범위/밀도/정규화 로직 반영
- `data/summarized/`, `data/verified/`, 기존 step4/5/summary 리포트 정리 후 Step 4 전체 재실행
- Step 4 첫 전체 재실행 결과에서 길이 위반 8건(`004`, `020`, `025`, `033`, `036`, `040`, `043`, `044`) 확인
- 위 8건은 `NewsSummarizer.summarize_model(...)` 경로로 타겟 재생성해 길이 계약 맞춤
- Step 5 전체 재검증 후 `046` 1건 suspicious 확인
- `046`은 `verify=True`로 재생성해 clean으로 교체
- `python3.11 evaluate.py` 재실행
- 수정 후 길이 분포를 `reports/length_distribution_after_tuning.json`으로 저장

최종 결과:
- Step 4: 글자수 통과 50/50, 위반율 0.0%
- Step 5: clean 50/50, suspicious 0/50
- 수정 전 → 수정 후 길이 분포 개선:
  - h34 평균 31.06 → 32.88, exact target 7 → 18, ±2 이내 16 → 47
  - h58 평균 52.74 → 55.66, exact target 1 → 10, ±2 이내 7 → 25
  - h89 평균 80.98 → 84.80, exact target 2 → 2, ±2 이내 5 → 15
- 최종 길이 위반 건수 0건
- `reports/summary.md`, `reports/step4_summary.json`, `reports/step5_verify.json` 최신화 완료

판단:
- 이번 이슈의 본질은 backend truncation이 아니라 summarizer가 하한/밀도 목표 없이 "짧아도 통과"시키던 설계였음
- 범위 검증 + densify retry + 공백 정규화로 목표 길이 근접도가 유의미하게 좋아졌음
- 이후 `pipeline/step4_summarize.py` 저장 정책도 보강해, 최종 재시도 후 길이 계약을 여전히 위반하는 결과는 `*_error.json`으로만 남기고 정상 요약 산출물로 저장하지 않도록 맞춤

### 01:38 KST — Step 4 저장 정책을 라이브러리 계약과 일치시킴
실행:
- `tests/test_step4_contract.py` 추가
- 길이 계약 위반 결과가 최종 재시도 뒤에도 남을 때 `process_file(...)`이 정상 요약 파일을 저장하지 않고 `*_error.json`만 남겨야 한다는 failing test를 먼저 작성
- `pipeline/step4_summarize.py`에서 최종 `violations`가 남아 있으면 `ValueError("Summary length contract violated after retries: ...")`를 발생시키도록 변경
- 변경 후 `pytest tests/test_step4_contract.py::test_process_file_writes_error_instead_of_saving_contract_violating_summary -q` 통과 확인
- 이어서 `pytest tests -q`와 `python3.11 -m py_compile pipeline/step4_summarize.py tests/test_step4_contract.py news_service.py news_schema.py` 통과 확인

결과:
- Step 4 배치 경로도 이제 라이브러리 경로와 동일하게 길이 계약 위반 결과를 정상 산출물로 저장하지 않음
- 향후 재실행 시 길이 위반은 `data/summarized/*_error.json`으로만 남아 후속 집계/교정 대상이 더 명확해짐

### 01:46 KST — evaluate 리포트에 headline 목표 근접도 집계 추가
실행:
- `tests/test_evaluate_metrics.py` 추가
- Step 4 평가 결과에 `headline_proximity`가 포함되고, markdown 리포트에 exact target / ±2 / ±4 지표가 출력되어야 한다는 failing test를 먼저 작성
- `evaluate.py`에 `HEADLINE_TARGETS`, `_build_proximity_metrics(...)` 추가
- `evaluate_step4()`가 `headline_34/58/89` 길이 기준으로 목표 근접도 지표를 함께 집계하도록 확장
- `write_markdown_report(...)`가 headline 목표 근접도 섹션을 렌더링하도록 확장
- `pytest tests/test_evaluate_metrics.py::test_evaluate_step4_returns_proximity_metrics_and_markdown -q`, `pytest tests -q`, `python3.11 evaluate.py`, `python3.11 -m py_compile evaluate.py tests/test_evaluate_metrics.py` 통과 확인
- `reports/length_distribution_after_tuning.json`도 현재 `data/summarized/*.json` 기준으로 재생성해 수치를 일치시킴

결과:
- `reports/step4_summary.json`에 `headline_proximity`가 추가됨
- `reports/summary.md`가 이제 headline 목표 근접도(h34/h58/h89의 exact, ±2, ±4)를 함께 보여줌
- 현재 실제 산출물 기준 근접도:
  - h34: exact 18 / ±2 47 / ±4 49
  - h58: exact 9 / ±2 25 / ±4 47
  - h89: exact 2 / ±2 15 / ±4 25

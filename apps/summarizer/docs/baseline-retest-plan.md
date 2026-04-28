# Baseline 재테스트 계획

최종 갱신: 2026-04-27 15:52:28 KST

> 목적: 현재 Hermit gateway + `glm-5.1` 기준으로 파이프라인 품질 기준선을 다시 만든다.

## 목표
- 기존 `data/raw/` 50개를 입력으로 사용해 Step 2~5를 다시 생성한다.
- `reports/`를 다시 생성해 현재 기준 baseline 품질을 확보한다.
- 이 결과를 바탕으로 프롬프트를 새로 쓸지, 부분 튜닝할지 결정한다.

## 재테스트 전제
- Python 실행은 반드시 `python3.11`
- LLM 호출은 `pipeline/common.py`를 통한 Hermit gateway
- 현재 기본 모델은 `glm-5.1`

## 재테스트 범위
### 포함
- Step 2: raw → JSON
- Step 3: JSON → score
- Step 4: JSON → summarize
- Step 5: summarize → verify
- evaluate.py 리포트 재생성

### 제외
- Step 1 신규 스크래핑
- 카테고리별 랭킹/서비스 노출 로직 구현
- prompt 재작성 자체

## 사전 체크리스트
- [ ] `python3.11` 사용 가능
- [ ] Hermit gateway 응답 가능
- [ ] `data/raw/` 50개 유지 확인
- [ ] 기존 산출물 보존/삭제 방침 정리

## 실행 순서
### 옵션 A: 기존 결과 보존 후 새로 실행
권장 방식.

1. 기존 출력 디렉터리 백업 또는 timestamp 이름으로 이동
2. 빈 상태에서 아래 실행
   - `python3.11 run_pipeline.py --step 2`
   - `python3.11 run_pipeline.py --step 3`
   - `python3.11 run_pipeline.py --step 4`
   - `python3.11 run_pipeline.py --step 5`
   - `python3.11 evaluate.py`
3. 결과를 `docs/progress-log.md`에 기록

### 옵션 B: 한 번에 재실행
- `python3.11 run_pipeline.py --from 2`
- `python3.11 evaluate.py`

장점:
- 단순함

주의:
- 특정 step에서 실패하면 중간 상태로 남을 수 있음

## 성공 기준
- Step 2 결과물이 전체 입력에 대해 일관되게 생성됨
- Step 3~5가 현재 기준으로 끝까지 실행됨
- `reports/summary.md`가 새 기준으로 재생성됨
- 품질 지표(글자 수 위반율, clean 비율)를 다시 확인 가능함

## baseline 이후 의사결정
재테스트가 끝나면 아래 중 하나를 선택한다.

1. `glm-5.1`에서 이미 충분히 안정적
- prompt는 최소 수정
- 테스트 도구와 문서 기준만 정리

2. 길이 위반/날짜 hallucination/JSON 파싱이 다시 많음
- summarizer prompt를 새로 설계
- 필요시 verify prompt도 분리 개선

3. 속도/품질이 불안정
- Hermit routing/model 전략 재검토
- 단, 현재 우선순위는 모델 교체보다 baseline 확보

# 뉴스 요약 파이프라인 현황

최종 갱신: 2026-04-27 15:52:28 KST

## 이 문서의 성격
이 문서는 현재 워킹 트리 기준의 실행 상태를 기록한다.
과거 Ollama/gemma 실험 기록은 참고용으로만 보며, 현재 공식 실행 기준은 Hermit gateway 기반이다.

## 현재 실행 기준
- LLM gateway: `http://localhost:8765/v1/chat/completions`
- 호출 모듈: `pipeline/common.py`
- 현재 기본 모델: `glm-5.1`
- 설정 소스: `~/.hermit/settings.json`
- provider 설정: `z.ai`
- 필수 Python 버전: `python3.11`

## 중요 주의사항
- 시스템 기본 `python3`가 3.9일 수 있으므로 파이프라인은 반드시 `python3.11`로 실행한다.
- `test_summarize.py`는 아직 Ollama 기준이라 현재 파이프라인 baseline 테스트의 공식 진입점이 아니다.

## 파이프라인 구조
```
원문 스크래핑 → JSON 변환 → 중요도 점수 → 요약(+인라인 검증) → 할루시네이션 검증
   step1          step2        step3          step4               step5
data/raw/       data/json/   data/scored/  data/summarized/    data/verified/
```

## 각 스텝 설명
| 스텝 | 파일 | 출력 | 비고 |
|------|------|------|------|
| 1 | `pipeline/step1_scrape.py` | `data/raw/{id}.txt` | 연합뉴스 기사 수집 |
| 2 | `pipeline/step2_to_json.py` | `data/json/{id}.json` | raw text → structured JSON |
| 3 | `pipeline/step3_score.py` | `data/scored/{id}.json` | 절대 평가 0~100점 |
| 4 | `pipeline/step4_summarize.py` | `data/summarized/{id}.json` | 헤드라인 3종 + summary + 인라인 검증 |
| 5 | `pipeline/step5_verify.py` | `data/verified/{id}.json` | 독립 할루시네이션 검증 |

## 현재 확인된 파일 상태
- `data/raw/`: 50개 존재
- `data/json/`: 일부만 존재
- `data/scored/`: 비어 있음
- `data/summarized/`: 비어 있음
- `data/verified/`: 비어 있음
- `data/summarized_backup_v1/`: 과거 50개 백업 존재
- `reports/`: 과거 평가 리포트 존재

## 해석
- 과거에는 50건 end-to-end 실행이 완료된 적이 있다.
- 현재 canonical output 디렉터리는 중간 상태다.
- 따라서 다음 우선순위는 프롬프트 수정이 아니라 baseline 재구성이다.

## 현재 목표
1. `python3.11` + Hermit gateway 기준으로 Step 2~5를 다시 실행한다.
2. `evaluate.py`로 baseline 리포트를 다시 생성한다.
3. 그 결과를 바탕으로 prompt 재작성 여부를 결정한다.

## 권장 실행 명령
- `python3.11 run_pipeline.py --step 2`
- `python3.11 run_pipeline.py --step 3`
- `python3.11 run_pipeline.py --step 4`
- `python3.11 run_pipeline.py --step 5`
- `python3.11 evaluate.py`

또는
- `python3.11 run_pipeline.py --from 2`
- `python3.11 evaluate.py`

## 연관 문서
- `docs/current-status.md`
- `docs/progress-log.md`
- `docs/baseline-retest-plan.md`
- `PRD.md`

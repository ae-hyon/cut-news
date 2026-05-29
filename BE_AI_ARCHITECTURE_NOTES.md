# Cut News BE / AI Architecture Evaluation Notes

## 한 줄 요약

Cut News는 AI가 생성한 뉴스를 그대로 노출하지 않고, 백엔드에서 수집·요약·검증·분류·스냅샷화하는 파이프라인을 통해 사용자별 아침 뉴스 피드를 안정적으로 제공하는 구조입니다.

---

## 1. 핵심기술

### Backend

- FastAPI 기반 REST API
- SQLAlchemy 기반 persistence / repository layer
- Pydantic 기반 domain model 및 API schema validation
- JWT 기반 인증 세션 관리
- Kakao OAuth 로그인 연동
- 사용자 관심사 기반 feed personalization
- 사용자별 daily feed snapshot / archive / read tracking

### AI / Pipeline

- Naver 뉴스 crawler artifact handoff
- AI summarizer pipeline
- verification stage를 통한 AI 결과 검증
- backend import quality gate
- daily feed snapshot generation
- run_report 기반 pipeline observability
- Hermes profile 기반 OAuth AI runtime 사용

---

## 2. 시스템 아키텍처 / AI 구조(BE)

### 2.1 단계형 AI 뉴스 파이프라인

뉴스 생성 흐름은 하나의 긴 작업이 아니라 단계별 책임이 분리된 파이프라인으로 구성되어 있습니다.

```text
GitHub Actions Crawl
  -> Crawler Artifact
  -> Local OAuth AI Summarizer
  -> Verification / Quality Gate
  -> Backend Import
  -> DailyFeedSnapshot Generation
  -> /v1/me/feed, /v1/me/archive
```

각 단계의 역할은 다음과 같습니다.

| 단계 | 역할 |
|---|---|
| Crawl | Naver 뉴스 원문 및 source metadata 수집 |
| Summarize | AI를 이용해 headline, summary, content 생성 |
| Verify | AI 생성 결과의 verdict/confidence 검증 |
| Import | DB 반영 전 category, quality gate, drop reason 처리 |
| Snapshot | 사용자별 daily feed를 고정된 snapshot으로 저장 |
| API | feed, archive, article detail, read state 제공 |

이 구조를 통해 AI 결과 생성, 검증, 저장, 사용자 노출이 분리되어 장애나 품질 문제를 단계별로 추적할 수 있습니다.

---

### 2.2 AI 결과 품질 게이트

AI 요약 결과는 바로 DB에 저장하지 않고 backend import 단계에서 품질 게이트를 거칩니다.

대표적인 방어 로직은 다음과 같습니다.

- verification verdict가 clean이 아닌 결과 차단
- confidence가 낮은 결과 차단
- 원문 title과 AI-generated headline/summary의 핵심 주제 불일치 차단
- mixed-content 또는 roundup 기사에서 다른 이슈가 headline 앞부분을 차지하는 경우 차단

예시 drop reason:

```text
quality_gate:verdict_not_clean
quality_gate:topic_mismatch
```

특히 `topic_mismatch` gate는 source title의 핵심 토픽과 생성된 headline/summary의 salient term overlap을 비교하여, 원문 기사와 다른 내용이 요약되어 사용자 피드에 노출되는 문제를 방지합니다.

평가 포인트:

> LLM 출력을 신뢰만 하는 구조가 아니라, BE import layer에서 deterministic validation을 적용해 hallucination/mixed-topic 결과를 차단합니다.

---

### 2.3 사용자별 Daily Feed Snapshot 구조

Cut News의 홈 피드는 매 요청마다 실시간으로 다시 계산되는 결과가 아니라, 사용자별로 생성된 `DailyFeedSnapshot`을 기반으로 제공됩니다.

주요 객체:

- `DailyFeedSnapshot`
- `DailyFeedSnapshotItem`
- `UserArticleRead`

이 구조의 장점:

- 같은 날짜의 피드를 안정적으로 재현 가능
- archive에서 과거 피드를 동일한 순서로 다시 조회 가능
- article detail 진입 시 snapshot 단위 read progress 기록 가능
- 모든 기사를 읽으면 snapshot completion 상태 관리 가능
- 사용자 preference가 나중에 바뀌어도 과거 피드 기록은 보존 가능

API 예시:

```text
GET /v1/me/feed
GET /v1/me/archive?month=YYYY-MM
GET /v1/me/archive/{YYYY-MM-DD}
GET /v1/me/articles/{article_id}?snapshot_id={snapshot_id}
```

평가 포인트:

> 사용자별 피드를 snapshot으로 고정해 추천 결과의 재현성, archive 일관성, read/completion 상태 관리를 동시에 해결했습니다.

---

### 2.4 feed_date와 published_at 분리

아침 뉴스 서비스에서는 사용자가 보는 피드 날짜와 실제 기사 발행일이 다를 수 있습니다.

예를 들어 2026-05-29 아침 피드는 상품 날짜는 2026-05-29이지만, 포함되는 기사는 대부분 2026-05-28 발행 기사입니다.

Cut News는 이를 다음처럼 분리했습니다.

| 개념 | 의미 |
|---|---|
| `feed_date` | 사용자가 보는 아침 피드 bucket 날짜 |
| `published_at` | 실제 기사 발행일 |

따라서 snapshot generation은 `feed_date`를 기준으로 사용자 피드 bucket을 만들되, 후보 기사는 product policy에 따라 전날 `published_at` 기사에서 선택합니다.

평가 포인트:

> 서비스 도메인 정책을 코드로 명시하여, 스케줄러가 생성한 피드와 사용자가 조회하는 피드의 날짜 불일치를 방지했습니다.

---

### 2.5 Evidence 기반 카테고리 분류

기사 category/subcategory는 단순 keyword matching만 사용하지 않습니다.

분류 우선순위:

1. 신뢰 가능한 source subcategory
2. crawler `source_query`가 title/summary에서 evidence term으로 뒷받침되는 경우
3. crawler `source_category`가 title/summary에서 evidence term으로 뒷받침되는 경우
4. broad keyword rule fallback

관측 지표:

```text
classification_source_counts.source_subcategory
classification_source_counts.crawler_source_query
classification_source_counts.crawler_source_category
classification_source_counts.keyword_rule
```

이 구조는 crawler query가 잘못 붙거나 원문 페이지에 related link/page chrome noise가 섞여 들어온 경우에도, 실제 title/summary가 이를 뒷받침하지 않으면 잘못된 category를 신뢰하지 않도록 설계되었습니다.

평가 포인트:

> crawler metadata와 기사 본문 evidence를 함께 사용해 category false positive를 줄이고, 분류 출처를 observability 지표로 남깁니다.

---

### 2.6 Pipeline observability

파이프라인은 성공 여부만 기록하지 않고, 품질과 운영 상태를 `run_report`에 남깁니다.

주요 지표:

- `status`
- `failed_step`
- `usable_imports`
- `drop_reason_counts`
- `quality_gate_skip_counts`
- `classification_source_counts`
- `snapshot_generation.attempted_user_count`
- `snapshot_generation.generated_count`
- `snapshot_generation.failed_count`

이를 통해 운영자는 다음 질문에 답할 수 있습니다.

- crawler는 정상적으로 데이터를 가져왔는가?
- AI summarizer는 몇 개의 사용 가능한 기사를 만들었는가?
- 어떤 이유로 기사가 drop되었는가?
- 모든 분류가 약한 keyword fallback에 의존하고 있지는 않은가?
- 사용자별 snapshot이 정상 생성되었는가?

평가 포인트:

> AI pipeline을 black box로 두지 않고, import/drop/classification/snapshot 지표를 기록해 운영 가능한 AI 시스템으로 설계했습니다.

---

### 2.7 GitHub Actions crawl-only + Local OAuth AI Runner

AI 요약은 GitHub Actions 내부에서 API key를 직접 사용하지 않고, trusted local/server runner의 OAuth AI runtime을 통해 수행합니다.

구조:

```text
GitHub Actions
  - crawl only
  - artifact upload

Trusted local/server machine
  - artifact download
  - Hermes profile AI summarization
  - backend import
  - snapshot generation
```

장점:

- GitHub Actions에 AI OAuth/session을 억지로 넣지 않아도 됨
- API key 노출 위험 감소
- AI runtime 교체 가능
- 운영자가 명시적으로 DB와 profile을 선택 가능
- crawl, summarize, import 책임이 분리됨

평가 포인트:

> crawler와 AI summarization runtime을 분리하여, OAuth 기반 AI 실행 환경과 서버 운영 환경의 제약을 안전하게 다뤘습니다.

---

## 3. 비용 최적화 + 품질 향상 계획

### 3.1 목표

현재 방향은 “모든 기사를 무조건 요약”하는 방식이 아니라, 전체 카테고리에서 충분히 크롤링한 뒤 저비용으로 먼저 후보를 평가하고, 실제 서비스에 필요한 기사만 고품질 요약하는 구조입니다.

핵심 목표:

- 사용자 수가 증가해도 LLM 요약 비용이 사용자 수에 비례하지 않도록 설계
- 전체 크롤링 기사 수가 늘어나도 full summarization 대상은 category-balanced top-K로 제한
- 중요한 기사에는 더 높은 품질 전략을 적용하고, 낮은 중요도 기사는 요약하지 않음
- 사용자별 DailyFeedSnapshot은 이미 검증된 article pool을 조합해 생성

요약 문장:

> LLM inference path와 personalization path를 분리합니다. 기사 단위 category/importance scoring으로 후보를 먼저 선별하고, 선별된 중요 기사만 고품질 요약한 뒤, 사용자별 DailyFeedSnapshot은 검증된 article reference만 선택합니다.

---

### 3.2 구현된 아키텍처: Candidate-first Summarization

```text
Crawl all categories
  -> normalize / dedupe
  -> cheap category + importance scoring
  -> per-category top-K candidate pool
  -> selected article high-quality summarization
  -> optional best-of-3 / selective retry
  -> verification / topic mismatch gate
  -> canonical verified article pool
  -> user preference based DailyFeedSnapshot
```

기존 단순 구조와의 차이:

| 구조 | 비용 특성 | 문제 |
|---|---|---|
| 전체 기사 요약 후 피드 구성 | 전체 크롤링 기사 수에 비례 | 필요 없는 기사까지 LLM 비용 발생 |
| 사용자별 요약 후 피드 구성 | 사용자 수 x 기사 수에 비례 | 사용자가 늘수록 비용 폭증 |
| candidate-first 구조 | 신규 중요 기사 후보 수에 비례 | category/top-K 정책 설계 필요 |

평가 포인트:

> 모든 기사를 요약하지 않고, 먼저 category/importance scoring으로 서비스 노출 후보를 선별합니다. 현재 구현은 `PIPELINE_SELECTED_PER_CATEGORY`로 Step 3 score 결과에서 category별 top-N만 Step 4 full summarization 대상으로 보냅니다. 이후 선별된 기사만 고품질 요약하므로 LLM 비용은 사용자 수가 아니라 신규 중요 기사 수에 비례합니다.

---

### 3.3 Category-balanced 후보 pool

중요도만 기준으로 global top-K를 뽑으면 경제/정치/테크 기사만 남고, 스포츠/라이프스타일/엔터테인먼트 선호 사용자의 피드가 부족할 수 있습니다.

따라서 후보 선별은 category-balanced top-K로 설계했고, 현재 Step 4에서 `PIPELINE_SELECTED_PER_CATEGORY=<N>`으로 활성화할 수 있습니다.

```text
for each category/subcategory:
  crawl many articles
  dedupe by normalized_url/content_hash
  score category confidence
  score importance
  keep top N candidates
```

예시 pool:

```text
stock: top 20
crypto: top 20
realestate: top 20
politics: top 20
economy: top 20
tech: top 20
entertainment: top 20
sports: top 20
global: top 20
lifestyle: top 20
```

사용자별 feed 생성:

```text
user preference
  -> select relevant category pools
  -> rank/mix/diversify
  -> create DailyFeedSnapshotItem(article_id, block_key, sort_order)
```

장점:

- 모든 사용자 카테고리에 대해 최소 기사 수 확보
- 개인화 단계에서 LLM 호출 없음
- 사용자 preference가 달라도 같은 verified article pool 재사용
- DailyFeedSnapshot은 article reference만 저장하므로 비용/저장공간 효율적

---

### 3.4 Category / Importance scoring 설계

pre-ranking 단계는 full summary보다 훨씬 저렴해야 합니다.

입력 후보:

- title
- source name
- source category
- source query
- published_at
- crawler snippet / description
- normalized URL
- duplicate cluster size
- category evidence terms
- 언론사 신뢰도 또는 source weight

출력 예시:

```json
{
  "article_id": "...",
  "primary_category": "tech",
  "subcategory": "tech-ai",
  "category_confidence": 0.91,
  "importance_score": 0.84,
  "importance_reason": "Major institute AI strategy announcement with policy/industry relevance",
  "should_summarize": true
}
```

초기 구현은 다음처럼 단계화합니다.

1. Rule-based + metadata scoring
   - source_query/source_category evidence
   - title keyword
   - duplicate count
   - source weight
2. Low-cost LLM scoring
   - title/snippet만 입력
   - JSON schema output
   - category confidence / importance score 산출
3. Full summarization target selection
   - category별 top-K
   - confidence threshold 통과
   - minimum article count 보장

평가 포인트:

> full summarization 전에 저비용 scoring layer를 둬서 LLM 비용을 줄이고, 사용자의 다양한 관심사에 대응할 수 있도록 category-balanced candidate pool을 확보합니다.

---

### 3.5 구현된 Selective best-of-N 요약 품질 전략

중요한 기사에는 단일 요약을 바로 사용하지 않고, 여러 요약 후보를 만든 뒤 가장 좋은 결과를 선택합니다.

현재 구현은 `PIPELINE_BEST_OF_N`과 `PIPELINE_BEST_OF_SCORE_THRESHOLD`로 제어합니다. 기본값은 비활성(single summary)이며, `PIPELINE_BEST_OF_N=3`처럼 켜도 Step 3 중요도 점수가 threshold 이상인 high-importance 기사에만 다중 후보를 생성합니다.

추천 정책:

| 기사 상태 | 요약 전략 |
|---|---|
| low importance | summarize 생략 |
| medium importance | single summary |
| high importance | best-of-3 summary candidates |
| verification low confidence | retry 또는 best-of-3 승격 |
| topic mismatch | drop 또는 stronger retry 후 재검증 |

Best-of-3 흐름:

```text
selected high-importance article
  -> generate summary candidate A
  -> generate summary candidate B
  -> generate summary candidate C
  -> judge candidates by factuality/readability/schema compliance
  -> select best final summary
  -> verification / topic_mismatch gate
  -> import canonical article
```

현재 selection 기준:

- inline verifier verdict가 `clean`이면 가장 높게 평가
- verifier confidence
- headline 길이 계약 통과 여부와 상한에 가까운 정보 밀도
- retry count가 적은 후보 우선
- 후보별 `_best_of_candidate_index`, `_best_of_quality_score`, `_best_of_candidates`를 summarized artifact에 남겨 audit 가능

추가 judge 기준으로 확장 가능한 항목:

- 원문 핵심 사실 보존
- 숫자/기관명/인물명 정확성
- headline과 summary의 주제 일관성
- 불필요한 추측 또는 과장 없음
- 서비스 톤 적합성
- category/subcategory와 내용의 정합성

Merge-of-3는 후보 간 공통 사실만 병합하는 방식으로 확장할 수 있지만, hallucination이 섞일 위험이 있어 초기에는 best-of-3 selection이 더 안전합니다.

평가 포인트:

> 모든 기사에 비싼 품질 전략을 적용하지 않고, 중요도가 높거나 검증 confidence가 낮은 기사에만 선택적으로 best-of-3 / retry를 적용해 비용과 품질을 동시에 관리합니다.

---

### 3.6 OAuth 기반 AI runtime 비용 절감 포인트

일반적인 LLM API는 호출량에 따라 직접 과금됩니다. Cut News는 이를 줄이기 위해 AI 실행 경로를 API key 기반 서버 호출로 고정하지 않고, OAuth 기반 AI runtime을 사용하는 로컬/운영 runner 구조를 채택했습니다.

구조:

```text
GitHub Actions
  - crawl only
  - no LLM API key required
  - artifact upload

Trusted local/server runner
  - Hermes profile / Codex OAuth runtime
  - summarization / verification
  - backend import
  - snapshot generation
```

어필 포인트:

- GitHub Actions에는 LLM API key를 저장하지 않음
- AI OAuth 세션이 있는 trusted runner에서만 요약 수행
- API-key direct billing path에 종속되지 않음
- provider/model/profile을 환경변수로 바꿀 수 있어 비용/품질 비교 가능
- 사용자별 snapshot 생성에는 LLM 호출이 없으므로 운영 비용이 안정적

표현할 때 주의할 점:

- “무료”라고 단정하지 않기
- “API key 직접 과금 방식 대신 OAuth 기반 런타임을 사용해 별도 API 호출 비용을 줄이는 구조”라고 표현
- 실제 비용 정책은 provider/OAuth plan에 따라 달라질 수 있으므로 “비용 최적화” 또는 “API 과금 최소화”로 표현

발표용 문장:

> 일반적인 LLM API 직접 호출 방식은 기사 수만큼 과금될 수 있기 때문에, Cut News는 GitHub Actions를 crawl-only로 제한하고 AI 요약은 OAuth 기반 Hermes/Codex runtime을 가진 trusted runner에서 수행하도록 분리했습니다. 또한 요약 대상 자체를 category-balanced top-K로 줄여 LLM 사용량을 제어했습니다.

---

### 3.7 작업 계획

#### Phase 1: 현재 구조 문서화 및 평가 자료 정리

**목표:** 발표/평가용 BE/AI 구조 문서를 완성합니다.

**파일:**

- Modify: `BE_AI_ARCHITECTURE_NOTES.md`
- Optional modify: `.dev/news-pipeline-quality-improvement-plan.md`

**작업:**

1. Candidate-first summarization 구조를 문서화합니다.
2. Category-balanced pool 개념을 문서화합니다.
3. Selective best-of-3 전략을 문서화합니다.
4. OAuth runtime 기반 비용 최적화 포인트를 문서화합니다.
5. 발표용 한 줄 문장과 평가 항목별 bullet을 정리합니다.

**권장 모델:**

- Model: `gpt-5.5`
- Provider/runtime: `openai-codex` 또는 현재 Hermes profile 기본값
- Effort: `low`
- 이유: 문서 정리 작업이라 복잡한 코드 추론이 필요하지 않음

**검증:**

```bash
git diff --check
```

---

#### Phase 2: Article candidate scoring 설계

**Status:** partially implemented. Step 3 scoring now preserves crawler metadata (`_source_category`, `_source_query`, `_content_source`) in scored outputs so Step 4 can select category-balanced candidates without rereading or resummarizing every article.

**목표:** full summarization 전에 category/importance를 산출하는 설계를 추가합니다.

**예상 파일:**

- Create: `apps/summarizer/pipeline/candidate_scoring.py`
- Create: `apps/summarizer/tests/test_candidate_scoring.py`
- Modify: `apps/summarizer/news_schema.py`
- Modify: `apps/summarizer/run_pipeline.py`
- Modify: `apps/backend/app/scripts/run_news_pipeline_job.py` 또는 pipeline report parser

**작업:**

1. Candidate scoring output schema 정의
   - `primary_category`
   - `subcategory`
   - `category_confidence`
   - `importance_score`
   - `should_summarize`
   - `reason`
2. rule/metadata 기반 scoring baseline 구현
3. JSON fixture로 category-balanced top-K selection 테스트 작성
4. run_report에 candidate scoring 지표 추가
   - crawled count
   - deduped count
   - candidate_scored count
   - selected_for_summary count
   - selected_by_category

**권장 모델:**

- Model: `gpt-5.5`
- Provider/runtime: `openai-codex`
- Effort: `medium`
- 이유: pipeline schema와 기존 summarizer flow를 건드리므로 구조 이해가 필요함

**검증:**

```bash
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q
python3 -m unittest tests/test_scheduled_artifact_pipeline.py -q
```

---

#### Phase 3: Category-balanced top-K selection 적용

**Status:** implemented for the summarization stage via `PIPELINE_SELECTED_PER_CATEGORY`. When set to a positive integer, Step 4 summarizes only the top scored articles per source category. If the variable is empty or no scored files are available, the pipeline preserves the previous behavior and summarizes all JSON articles.

**목표:** 모든 크롤링 기사를 요약하지 않고, category별 최소 후보 pool만 요약 대상으로 넘깁니다.

**예상 파일:**

- Modify: `apps/summarizer/run_pipeline.py`
- Modify: `apps/summarizer/pipeline/*`
- Create/modify: `apps/summarizer/tests/test_candidate_selection.py`
- Modify: `scripts/check-pipeline-report.py`

**작업:**

1. category별 top-K config 추가
   - 예: `PIPELINE_SELECTED_PER_CATEGORY=20`
   - optional: `PIPELINE_SELECTED_PER_SUBCATEGORY`
2. selected candidate만 summarization stage로 전달
3. category별 부족분 처리 정책 추가
   - 부족하면 있는 만큼만 사용
   - critical category 부족 경고
4. report warning 추가
   - `category_candidate_shortage`
   - `selected_for_summary_by_category`

**권장 모델:**

- Model: `gpt-5.5`
- Provider/runtime: `openai-codex`
- Effort: `medium`
- 이유: 비용 최적화 핵심 구현이며 pipeline stage boundary가 중요함

**검증:**

```bash
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q
make local-report-check REPORT_CHECK_ARGS=--require-uncapped
```

---

#### Phase 4: Selective best-of-3 summarization 설계 및 구현

**목표:** 모든 기사에 3회 요약을 적용하지 않고, 중요도가 높은 기사 또는 검증이 불안정한 기사에만 다중 후보 요약을 적용합니다.

**예상 파일:**

- Modify: `apps/summarizer/pipeline/common.py`
- Modify: `apps/summarizer/run_pipeline.py`
- Modify: `apps/summarizer/news_schema.py`
- Create: `apps/summarizer/tests/test_best_of_summary.py`

**작업:**

1. summary generation candidate N 설정 추가
   - `PIPELINE_BEST_OF_N=1|3`
   - `PIPELINE_BEST_OF_MIN_IMPORTANCE=0.80`
2. high-importance 기사만 N개 summary candidate 생성
3. judge prompt 또는 deterministic scoring으로 best candidate 선택
4. final verification stage는 기존 quality gate 재사용
5. report에 best-of-N 사용량 추가
   - `best_of_attempted_count`
   - `best_of_selected_count`
   - `best_of_fallback_count`

**권장 모델:**

- Summary candidates:
  - Model: `gpt-5.5` 또는 current profile default
  - Effort: `medium`
- Judge:
  - Model: `gpt-5.5`
  - Effort: `high`
- 이유: judge는 사실성/일관성 판단이 중요하므로 candidate 생성보다 높은 reasoning이 유리함

**비용 정책:**

- default는 single summary
- high importance만 best-of-3
- verification 실패 시에만 retry 승격

**검증:**

```bash
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q
```

Disposable DB로 실제 run_report 확인:

```bash
QUALITY_DB="$PWD/apps/backend/dev-quality-flow.db" \
HOME=/Users/reddit \
DATABASE_URL="sqlite+pysqlite:///$QUALITY_DB" \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
PIPELINE_MAX_WORKERS=3 \
make ops-pipeline-from-github
```

---

#### Phase 5: Backend import / snapshot 재사용 보강

**목표:** 사용자별 snapshot 생성 시 LLM 결과를 절대 재생성하지 않고 canonical article pool만 참조하도록 보강합니다.

**예상 파일:**

- Modify: `apps/backend/app/application/services/article_ingest_service.py`
- Modify: `apps/backend/app/application/services/daily_feed_snapshot_service.py`
- Modify: `apps/backend/tests/test_article_ingest_service.py`
- Modify: `apps/backend/tests/test_daily_feed_snapshot_service.py`

**작업:**

1. import된 article이 canonical AI result임을 명확히 문서화
2. `DailyFeedSnapshotItem`은 article reference만 저장하는 정책 유지
3. snapshot generation에서 LLM/summarizer 경로를 호출하지 않는 regression test 추가
4. article pool 부족 시 empty/partial snapshot 정책 명확화

**권장 모델:**

- Model: `gpt-5.5`
- Provider/runtime: `openai-codex`
- Effort: `medium`
- 이유: backend service contract와 tests를 함께 봐야 함

**검증:**

```bash
cd apps/backend && PYTHONPATH=. uv run pytest tests/test_article_ingest_service.py tests/test_daily_feed_snapshot_service.py -q
cd apps/backend && PYTHONPATH=. uv run pytest tests/ -q
```

---

#### Phase 6: 고정 artifact 기반 비용/품질 평가

**목표:** 같은 crawl artifact에 대해 비용과 품질을 비교해 정책을 선택합니다.

**예상 파일:**

- Create: `.dev/news-pipeline-cost-quality-eval.md`
- Create: `.dev/news-pipeline-cost-quality-eval.json`
- Optional create: `scripts/evaluate-pipeline-variants.py`

**비교 후보:**

| Variant | Scoring | Summary | Best-of | 예상 비용 | 목적 |
|---|---|---|---|---|---|
| baseline | 없음 | 전체 기사 | 없음 | 높음 | 현재 대비 기준 |
| candidate-first | rule/metadata | selected only | 없음 | 낮음 | 비용 절감 |
| selective quality | rule/metadata + LLM scoring | selected only | high importance only | 중간 | 품질/비용 균형 |
| max quality | LLM scoring | selected only | best-of-3 broad | 높음 | 품질 상한 확인 |

**권장 모델:**

- Evaluation runner: `gpt-5.5`
- Effort: `high`
- 이유: 여러 run_report와 output 품질을 비교하고 정책 판단이 필요함

**검증 지표:**

- selected_for_summary / crawled ratio
- estimated LLM calls
- usable_imports
- drop_reason_counts
- topic_mismatch count
- category coverage
- category_candidate_shortage
- summary length violations
- manual sample quality score
- final feed count per preference profile

---

### 3.8 최종 발표용 문장

짧은 버전:

> Cut News는 모든 크롤링 기사를 무조건 요약하지 않고, 먼저 카테고리와 중요도를 평가해 카테고리별 top-K 후보를 선별한 뒤, 실제 서비스에 필요한 기사만 고품질 요약합니다.

긴 버전:

> Cut News는 사용자별 피드 생성 시 LLM을 호출하지 않습니다. 전체 카테고리에서 크롤링한 기사에 대해 먼저 저비용 category/importance scoring을 수행하고, 카테고리별 최소 후보 pool을 확보한 뒤 선별된 기사만 요약합니다. 중요도가 높은 기사는 best-of-3 후보 중 judge/verification을 통과한 결과를 사용하며, 최종 결과는 topic mismatch와 verdict quality gate를 통과해야 DB에 저장됩니다. 사용자별 DailyFeedSnapshot은 이 검증된 article pool에서 article reference만 선택하므로, LLM 비용은 사용자 수가 아니라 신규 중요 기사 수에 비례합니다.

평가 포인트 bullet:

- Candidate-first summarization으로 전체 기사 요약 비용 절감
- Category-balanced pool로 사용자 preference 다양성 보장
- Selective best-of-3로 중요 기사 품질 향상
- OAuth 기반 Hermes/Codex runtime으로 직접 LLM API key 과금 경로 최소화
- Canonical verified article pool 재사용으로 사용자별 snapshot 생성 비용 절감
- run_report로 비용/품질/coverage 지표 관측 가능

---

## 4. Backend Layering

Backend는 다음 레이어로 분리되어 있습니다.

```text
presentation/api/routes
  -> application/services
  -> domain/entities, domain/repositories
  -> infrastructure/repositories, database models
```

예시:

| Layer | 역할 | 예시 |
|---|---|---|
| Presentation | API request/response contract | `users.py`, `articles.py`, `auth.py` |
| Application | Use case orchestration | `DailyFeedSnapshotService`, `ArticleIngestService`, `FeedService` |
| Domain | 핵심 entity / repository contract | `DailyFeedSnapshot`, `Article`, `UserPreference` |
| Infrastructure | DB model / repository implementation | SQLAlchemy repositories/models |

평가 포인트:

> API route는 계약 처리에 집중하고, 피드 생성·기사 import·스냅샷 생성·인증 세션 로직은 application service로 분리했습니다.

---

## 5. BE 품질 관리 / 테스트 전략

실제 발견된 품질 이슈를 fixture와 regression test로 고정했습니다.

테스트 대상 예시:

- article ingest quality gate
- category classification false positive
- topic mismatch drop
- daily feed snapshot generation
- feed_date / published_at mapping
- pipeline run_report parsing
- authenticated feed/archive/article detail API contract

최근 확인된 backend gate:

```text
git diff --check: pass
focused backend tests: 38 passed
full backend tests: 129 passed
```

평가 포인트:

> 뉴스 품질 이슈를 수동 운영 이슈로만 두지 않고, backend regression test로 전환해 재발을 방지했습니다.

---

## 6. 발표용 핵심 문장

### 짧은 버전

Cut News는 AI가 생성한 뉴스를 그대로 보여주는 서비스가 아니라, 백엔드에서 검증·분류·스냅샷화하여 사용자별 아침 피드로 안정적으로 제공하는 AI 뉴스 파이프라인입니다.

### 조금 긴 버전

Cut News의 BE/AI 구조는 GitHub Actions 기반 뉴스 수집, OAuth 기반 로컬 AI 요약, verification, import quality gate, 사용자별 daily feed snapshot으로 구성됩니다. LLM 출력은 DB 저장 전 verdict, confidence, topic mismatch gate를 통과해야 하며, 모든 import/drop/classification/snapshot 결과는 run_report로 남겨 운영자가 품질을 추적할 수 있습니다.

---

## 7. 평가 항목별 추천 정리

### 핵심기술

- FastAPI REST API
- SQLAlchemy repository pattern
- Pydantic domain/schema validation
- JWT + Kakao OAuth 인증
- 사용자 preference 기반 feed personalization
- DailyFeedSnapshot 기반 archive/read tracking
- AI summarizer pipeline
- run_report observability

### 시스템아키텍처 / AI구조(BE)

- Crawl → Summarize → Verify → Import → Snapshot 단계형 pipeline
- GitHub Actions crawl-only + local OAuth AI runner 분리
- LLM output quality gate
- `topic_mismatch` 기반 mixed-summary 차단
- evidence 기반 category classification
- feed_date / published_at 분리
- 사용자별 snapshot 기반 피드 재현성 확보

### 가장 강조할 Top 3

1. AI 결과 품질 게이트: LLM hallucination/mixed-topic 결과를 BE import 단계에서 차단
2. Daily Feed Snapshot: 사용자별 피드 재현성, archive, read tracking을 안정적으로 관리
3. Pipeline observability: run_report로 import/drop/classification/snapshot 품질 지표 추적

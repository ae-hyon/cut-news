# Summary Sequence

최종 갱신: 2026-04-28 02:13:14 KST

## 목적
core-backend -> news_summurizer 호출 경로와 실패 분기를 텍스트 시퀀스로 남긴다.

## 성공 경로
1. Client 또는 내부 운영 호출이 `POST /v1/summaries` 요청을 보낸다.
2. FastAPI route `app/presentation/api/routes/summaries.py`가 `SummaryRequestSchema`로 입력을 검증한다.
3. route는 `SummaryGatewayService.summarize(payload)`를 호출한다.
4. `SummaryGatewayService`는 입력이 Pydantic model이면 `model_dump(mode='json', exclude_none=True)`로 API payload를 정규화한다.
5. service는 `NEWS_SUMMARIZER_DIR`를 `sys.path`에 추가한다.
6. service는 sibling 프로젝트에서 다음을 import 한다.
   - `news_adapter.summarize_request`
   - `news_schema.NewsArticle`
   - `news_schema.SummarizeRequest`
   - `news_schema.SummarizerSettings`
7. service는 API payload를 summarizer typed model로 변환한다.
   - article -> `NewsArticle`
   - request -> `SummarizeRequest`
   - runtime -> `SummarizerSettings`
8. service는 `summarize_request(request, runtime)`를 호출한다.
9. sibling summarizer는 `SummaryResult`를 반환한다.
10. route는 결과가 Pydantic model이면 `model_dump(by_alias=True)`로 풀어서 `SummaryResponseSchema`로 다시 검증한다.
11. 검증이 통과하면 FastAPI가 200 response를 반환한다.

## 경계별 책임
- presentation request schema:
  - 클라이언트 입력 형식 검증
- application summary gateway service:
  - API schema -> summarizer schema 변환
  - runtime setting 조립
  - sibling library 호출
- presentation response schema:
  - backend가 외부 라이브러리 결과를 마지막으로 다시 검증

## contract violation 경로
1. sibling summarizer가 결과를 반환한다.
2. 그 결과가 API가 요구하는 필드/alias/길이 계약을 만족하지 못한다.
3. route의 `SummaryResponseSchema.model_validate(...)`에서 `PydanticValidationError`가 발생한다.
4. backend는 다음 표준 502 payload를 반환한다.
   - `code=summary_contract_violation`
   - `message=Summary response did not satisfy the required schema.`
   - `details=<validation error text>`

## 일반 실패 경로
1. import 실패, runtime 설정 문제, library 예외, LLM 호출 실패 등으로 `service.summarize(...)` 또는 route 내부에서 일반 예외가 발생한다.
2. backend는 다음 표준 502 payload를 반환한다.
   - `code=summary_generation_failed`
   - `message=Summary generation failed.`
   - `details=<exception text>`

## `_error` 산출물과의 관계
- `*_error.json`은 `news_summurizer`의 오프라인 pipeline(step2~step5) 산출물 개념이다.
- core-backend의 `/v1/summaries`는 파일 산출물을 직접 다루지 않는다.
- 대신 online request 경로에서는 예외를 받아 502 JSON error payload로 표준화한다.
- 즉, 오프라인 pipeline에서는 `_error.json`, online API에서는 `ErrorResponseSchema`가 같은 실패를 각 환경에 맞게 표현한다.

## 현재 운영 해석
- 파일 기반 `_error.json`은 배치/파이프라인 디버깅에 적합하다.
- `ErrorResponseSchema`는 앱/백엔드 API 소비자에게 적합하다.
- 두 표현은 동일한 근본 원인(LLM 호출 실패, contract violation, 환경 문제)을 서로 다른 채널에서 전달한다.

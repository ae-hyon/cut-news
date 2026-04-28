# 서비스 응답 조립 계층

이 문서는 현재 파이프라인 산출물(`data/json`, `data/scored`, `data/summarized`, `data/verified`)을
실제 서비스 응답 JSON으로 묶는 방법을 설명한다.

## 목적

현재 파이프라인은 기사 1건 단위 산출물까지만 만든다.
서비스 화면 요구사항인 `넓게보기`, `깊게보기`는 별도의 조립 계층이 필요하다.

이를 위해 `service_response.py`를 추가했다.

역할:
- 기사 본문/점수/요약/검증 결과를 article card로 병합
- 카테고리 메타데이터를 기준으로 대분류/중분류 묶음 생성
- `넓게보기` 응답 JSON 생성
- `깊게보기` 응답 JSON 생성
- 중분류 기사가 부족할 때 대분류 기사로 fallback 채움

## 입력

### 1) 파이프라인 산출물
- `data/json/<article_id>.json`
- `data/scored/<article_id>.json`
- `data/summarized/<article_id>.json`
- `data/verified/<article_id>.json`

### 2) 카테고리 메타데이터
기본 경로:
- `data/category_map.json`

템플릿:
- `data/category_map.template.json`

형식:
```json
[
  {
    "article_id": "001",
    "primary_category": "정치",
    "subcategory": "청와대"
  }
]
```

규칙:
- `article_id`: `001` 같은 3자리 문자열
- `primary_category`: 넓게보기 대분류
- `subcategory`: 깊게보기 중분류. 없으면 빈 문자열 가능

현재 포함된 파일:
- `data/category_map.template.json` — 형식 예시
- `data/category_map.json` — 현재 50건 기준 카테고리 맵 초안

주의:
- `data/category_map.json`은 현재 기사 제목/내용 기준으로 정리한 초안이다.
- 실제 서비스 taxonomy가 확정되면 대분류/중분류 명칭은 다시 맞춰야 한다.

## 선택 규칙

### 공통
- 기본적으로 `verified.verdict == clean` 인 기사만 포함
- 기본 정렬 기준: `score` 내림차순 → `date` → `article_id`
- `--min-score`로 최소 점수 컷 적용 가능

### 넓게보기
- 대분류별로 기사 최대 5개 반환
- 각 대분류 내부에서는 점수 상위 기사부터 선택

### 깊게보기
- `primary_category + subcategory`를 먼저 선택
- 해당 중분류 기사가 5개 미만이면 같은 대분류의 다른 기사로 남은 슬롯 채움
- 중복 article_id는 제외

## CLI 사용법

### 넓게보기
```bash
python3.11 service_response.py --metadata data/category_map.json --mode wide --pretty
```

### 깊게보기
```bash
python3.11 service_response.py \
  --metadata data/category_map.json \
  --mode deep \
  --primary 경제 \
  --subcategory 금융 \
  --pretty
```

### suspicious 포함
```bash
python3.11 service_response.py --metadata data/category_map.json --mode wide --include-suspicious --pretty
```

## 출력 스키마

### 넓게보기
```json
{
  "mode": "wide",
  "top_n": 5,
  "categories": [
    {
      "primary_category": "경제",
      "article_count": 10,
      "subcategories": ["금융", "산업"]
    }
  ],
  "sections": [
    {
      "primary_category": "경제",
      "article_count": 5,
      "articles": [
        {
          "article_id": "012",
          "primary_category": "경제",
          "subcategory": "산업",
          "title": "...",
          "date": "2026-04-24",
          "author": "...",
          "url": "...",
          "score": 96,
          "score_reason": "...",
          "headline_34": "...",
          "headline_58": "...",
          "headline_89": "...",
          "summary": "...",
          "verification": {
            "verdict": "clean",
            "hallucinations": [],
            "confidence": 98
          }
        }
      ]
    }
  ]
}
```

### 깊게보기
```json
{
  "mode": "deep",
  "top_n": 5,
  "primary_category": "경제",
  "subcategory": "금융",
  "sub_articles": 3,
  "parent_fill_articles": 2,
  "categories": [...],
  "articles": [...]
}
```

## 현재 상태

완료:
- 응답 조립 모듈 구현 완료 (`service_response.py`)
- 카테고리 메타데이터 템플릿 추가 완료 (`data/category_map.template.json`)
- 실제 기사 50건용 카테고리 맵 초안 작성 완료 (`data/category_map.json`)
- wide / deep 모드 실행 검증 완료

남은 일:
- 실제 서비스 taxonomy에 맞춰 `data/category_map.json` 명칭 조정
- 필요하면 이 모듈을 FastAPI/웹 응답 계층에 연결

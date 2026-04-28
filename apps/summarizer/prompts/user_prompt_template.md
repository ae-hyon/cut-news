# User Prompt Template

LLM에 기사를 전달할 때 아래 형식을 사용합니다.
`{...}` 부분을 실제 기사 데이터로 채워서 전송합니다.

---

## User Prompt

```
다음 뉴스 기사를 요약해주세요.

{
  "title": "{기사 제목}",
  "date": "{YYYY-MM-DD}",
  "author": "{기자명}",
  "content": "{기사 본문 plain text}"
}
```

---

## 참고: Python 코드 예시

```python
import json

def build_user_prompt(title: str, date: str, author: str, content: str) -> str:
    article = {
        "title": title,
        "date": date,
        "author": author,
        "content": content,
    }
    return f"다음 뉴스 기사를 요약해주세요.\n\n{json.dumps(article, ensure_ascii=False, indent=2)}"
```

---

## LLM 응답 파싱 예시

```python
import json

def parse_summary_response(response_text: str) -> dict:
    """LLM이 반환한 JSON 문자열을 파싱합니다."""
    return json.loads(response_text.strip())

# 예상 응답 구조:
# {
#   "headline_34": "...",   # ≤34자
#   "headline_58": "...",   # ≤58자
#   "headline_89": "...",   # ≤89자
#   "summary": "..."        # 80~200자 권장
# }
```

"""저장/조회 없이 기사 입력을 받아 요약만 수행하는 라이브러리.

메인 백엔드 서버에서 import 해서 바로 사용할 수 있도록 설계했다.
주요 자원은 DB 자원이 아니라 입력 기사(article)와 생성 결과(summary)다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from news_schema import HEADLINE_LIMITS, NewsArticle, SummaryResult, VerificationResult, normalize_text

PREFERRED_HEADLINE_FLOORS = {
    "headline_34": 32,
    "headline_58": 54,
    "headline_89": 82,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "summarizer_system.md").read_text(encoding="utf-8")

VERIFY_SYSTEM = """당신은 팩트체크 전문가입니다. 뉴스 기사 원문과 요약문을 비교하여
요약문에서 사실이 틀리거나 왜곡된 내용을 찾아냅니다.

규칙:
- 표현이 달라도 사실이 일치하면 할루시네이션이 아닙니다.
- 수치·날짜·인물·기관이 원문과 다르게 기술된 경우만 할루시네이션입니다.
- 원문에 없는 사실(새로운 사건, 없는 수치 등)을 추가한 경우만 할루시네이션입니다.
- 반드시 JSON으로만 응답하세요:

{
  \"verdict\": \"clean\" 또는 \"suspicious\",
  \"hallucinations\": [\"사실 오류 내용1\", \"사실 오류 내용2\"],
  \"confidence\": 0~100
}"""


class NewsSummaryError(Exception):
    pass


class NewsSummarizer:
    def __init__(
        self,
        *,
        backend: str = "codex_exec",
        model: str = "gpt-5.4-mini",
        reasoning_effort: str = "low",
        timeout: int = 300,
    ):
        self.backend = backend
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout

    def summarize(self, article: dict[str, Any], *, verify: bool = False, max_retries: int = 2) -> dict[str, Any]:
        article_model = self._coerce_article(article)
        return self.summarize_model(article_model, verify=verify, max_retries=max_retries).model_dump(by_alias=True)

    def summarize_model(self, article: NewsArticle, *, verify: bool = False, max_retries: int = 2) -> SummaryResult:
        self._configure_runtime()
        from pipeline.common import call_llm, parse_json_response

        article_payload = article.model_dump(mode="json", exclude_none=True)
        user_prompt = self._build_initial_prompt(article_payload)
        verify_result: VerificationResult | None = None

        for attempt in range(max_retries + 1):
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.3, timeout=self.timeout)
            result = parse_json_response(raw)
            self._normalize_result_texts(result)
            self._apply_length_checks(result)

            violations = result.get("_violations", [])
            if violations and attempt < max_retries:
                user_prompt = self._build_length_retry_prompt(article_payload, result, violations)
                continue

            density_feedback = self._build_density_retry_prompt(article_payload, result)
            if density_feedback and attempt < max_retries:
                user_prompt = density_feedback
                continue

            if verify:
                verify_result = self.verify_model(article, result)
                if verify_result.verdict == "suspicious" and attempt < max_retries:
                    user_prompt = self._build_retry_prompt(article_payload, verify_result.hallucinations)
                    continue

            result["_verify"] = (verify_result or VerificationResult(verdict="skipped", hallucinations=[], confidence=0)).model_dump()
            result["_retry_count"] = attempt
            return SummaryResult.model_validate(result)

        raise NewsSummaryError("요약 생성 실패")

    def verify(self, article: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        article_model = self._coerce_article(article)
        return self.verify_model(article_model, summary).model_dump()

    def verify_model(self, article: NewsArticle, summary: SummaryResult | dict[str, Any]) -> VerificationResult:
        self._configure_runtime()
        from pipeline.common import call_llm, parse_json_response

        article_payload = article.model_dump(mode="json", exclude_none=True)
        if isinstance(summary, SummaryResult):
            summary_payload = summary.model_dump(by_alias=True)
        else:
            summary_payload = dict(summary)

        summary_text = "\n".join([
            f"headline_34: {summary_payload.get('headline_34', '')}",
            f"headline_58: {summary_payload.get('headline_58', '')}",
            f"headline_89: {summary_payload.get('headline_89', '')}",
            f"summary: {summary_payload.get('summary', '')}",
        ])
        user_prompt = (
            f"[원문]\n제목: {article_payload.get('title', '')}\n"
            f"본문: {article_payload.get('content', '')}\n\n"
            f"[요약문]\n{summary_text}\n\n"
            "요약문에서 원문에 없는 내용을 찾아주세요."
        )
        raw = call_llm(VERIFY_SYSTEM, user_prompt, temperature=0.1, timeout=self.timeout)
        return VerificationResult.model_validate(parse_json_response(raw))

    def summarize_file(self, file_path: str | Path, *, verify: bool = False, max_retries: int = 2) -> dict[str, Any]:
        article = self.load_article_file(file_path)
        return self.summarize(article, verify=verify, max_retries=max_retries)

    def summarize_file_model(self, file_path: str | Path, *, verify: bool = False, max_retries: int = 2) -> SummaryResult:
        article = self.load_article_file_model(file_path)
        return self.summarize_model(article, verify=verify, max_retries=max_retries)

    def summarize_url(self, url: str, *, verify: bool = False, max_retries: int = 2) -> dict[str, Any]:
        article = self.fetch_article(url)
        return self.summarize(article, verify=verify, max_retries=max_retries)

    def summarize_url_model(self, url: str, *, verify: bool = False, max_retries: int = 2) -> SummaryResult:
        article = self.fetch_article_model(url)
        return self.summarize_model(article, verify=verify, max_retries=max_retries)

    @staticmethod
    def load_article_file(file_path: str | Path) -> dict[str, Any]:
        return NewsSummarizer.load_article_file_model(file_path).model_dump(mode="json", exclude_none=True)

    @staticmethod
    def load_article_file_model(file_path: str | Path) -> NewsArticle:
        return NewsArticle.model_validate(json.loads(Path(file_path).read_text(encoding="utf-8")))

    @staticmethod
    def fetch_article(url: str) -> dict[str, Any]:
        return NewsSummarizer.fetch_article_model(url).model_dump(mode="json", exclude_none=True)

    @staticmethod
    def fetch_article_model(url: str) -> NewsArticle:
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            raise NewsSummaryError(
                "URL 크롤링에는 beautifulsoup4가 필요합니다. `python3.11 -m pip install beautifulsoup4` 후 다시 실행하세요."
            ) from e

        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_el = soup.select_one("h1.tit") or soup.select_one(".article-tit") or soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else "(제목 없음)"

        date_el = soup.select_one(".update-time") or soup.select_one("time") or soup.select_one(".article-info .date")
        date = date_el.get_text(strip=True) if date_el else ""

        author_el = soup.select_one(".writer") or soup.select_one(".byline")
        author = author_el.get_text(strip=True) if author_el else ""

        body = soup.select_one(".article") or soup.select_one(".article-txt") or soup.select_one("article")
        if body:
            for tag in body.select("figure, .sns-wrap, .copyright, script, style, .ad"):
                tag.decompose()
            content = body.get_text(separator=" ", strip=True)
        else:
            content = ""

        return NewsArticle.model_validate(
            {
                "title": title,
                "date": date,
                "author": author,
                "url": url,
                "content": content,
            }
        )

    def _configure_runtime(self) -> None:
        os.environ["PIPELINE_LLM_BACKEND"] = self.backend
        os.environ["PIPELINE_MODEL"] = self.model
        os.environ["PIPELINE_CODEX_REASONING_EFFORT"] = self.reasoning_effort

    @staticmethod
    def _coerce_article(article: NewsArticle | dict[str, Any]) -> NewsArticle:
        if isinstance(article, NewsArticle):
            return article
        try:
            return NewsArticle.model_validate(article)
        except Exception as e:
            raise NewsSummaryError(f"article 스키마 검증 실패: {e}") from e

    @staticmethod
    def _build_initial_prompt(article: dict[str, Any]) -> str:
        extra_rules = [
            "반드시 원문에 있는 사실만 사용하세요.",
            "원문에 없는 해석, 배경 추론, 일반적 주의 문구를 추가하지 마세요.",
            "headline_34는 29~34자, headline_58은 50~58자, headline_89는 76~89자 범위를 반드시 지키세요.",
            "세 headline 모두 범위만 맞추지 말고 가능한 한 상한에 가깝게 채우세요.",
            "짧다고 느슨하게 끝내지 말고, 원문 사실을 더 넣어 의미 밀도를 높이세요.",
        ]

        title = article.get("title", "")
        content = article.get("content", "")
        if title.startswith("[인사]"):
            extra_rules.append("인사 기사이므로 '재편', '정비', '마무리' 같은 해석 표현을 넣지 말고 실제 인사 대상과 직책만 요약하세요.")
        if "풍랑주의보" in title or "풍랑주의보" in content:
            extra_rules.append("기상 기사이므로 원문에 없는 '주의 필요', '안전 유의' 같은 상식적 권고를 추가하지 마세요.")

        return (
            "다음 뉴스 기사를 요약해주세요.\n"
            "추가 규칙:\n- " + "\n- ".join(extra_rules) + "\n\n"
            f"{json.dumps(article, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _build_length_retry_prompt(article: dict[str, Any], result: dict[str, Any], violations: list[str]) -> str:
        guidance = []
        for violation in violations:
            field = violation.split(":", 1)[0]
            current_len = result.get(f"_{field}_len", len(result.get(field, "")))
            min_len, max_len = HEADLINE_LIMITS[field]
            if current_len < min_len:
                guidance.append(
                    f"- {field}: 현재 {current_len}자입니다. 원문 사실을 1개 더 포함해 {max_len - 1}~{max_len}자에 가깝게 늘리세요. 군더더기 대신 구체 명사, 주체, 결과를 보강하세요."
                )
            elif current_len > max_len:
                guidance.append(
                    f"- {field}: 현재 {current_len}자입니다. 핵심 사실은 유지하고 수식어를 줄여 {max_len - 1}~{max_len}자로 줄이세요."
                )
        guidance_text = "\n".join(guidance) if guidance else "- 세 headline 모두 요구 범위를 다시 정확히 맞추세요."
        return (
            "다음 뉴스 기사를 다시 요약해주세요.\n"
            "이전 응답은 headline 길이 목표를 정확히 맞추지 못했습니다.\n"
            "핵심 사실은 유지하되 원문 사실만 사용하세요.\n"
            "headline_34는 29~34자, headline_58은 50~58자, headline_89는 76~89자 범위를 반드시 맞추고, 가능하면 상한에 가깝게 채우세요.\n"
            "아래 지시를 그대로 반영하세요.\n"
            f"{guidance_text}\n"
            f"현재 위반: {violations}\n"
            f"이전 응답: {json.dumps(result, ensure_ascii=False)}\n\n"
            f"기사: {json.dumps(article, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _build_density_retry_prompt(article: dict[str, Any], result: dict[str, Any]) -> str | None:
        guidance = []
        for field, preferred_floor in PREFERRED_HEADLINE_FLOORS.items():
            current_len = result.get(f"_{field}_len", len(result.get(field, "")))
            _, max_len = HEADLINE_LIMITS[field]
            if current_len < preferred_floor:
                guidance.append(
                    f"- {field}: 현재 {current_len}자입니다. 범위는 맞더라도 아직 짧습니다. 원문 사실을 더 넣어 {preferred_floor}~{max_len}자 쪽으로 밀도 있게 늘리세요."
                )
        if not guidance:
            return None
        guidance_text = "\n".join(guidance)
        return (
            "다음 뉴스 기사를 다시 요약해주세요.\n"
            "이전 응답은 허용 범위 안이지만 headline 길이가 아직 너무 짧습니다.\n"
            "원문에 있는 사실만 사용해 더 구체적이고 밀도 있게 작성하세요.\n"
            "불필요한 수식어 대신 주체, 대상, 결과, 장소 같은 핵심 사실을 보강하세요.\n"
            f"{guidance_text}\n"
            f"이전 응답: {json.dumps(result, ensure_ascii=False)}\n\n"
            f"기사: {json.dumps(article, ensure_ascii=False, indent=2)}"
        )

    @staticmethod
    def _build_retry_prompt(article: dict[str, Any], hallucinations: list[str]) -> str:
        issues = "\n".join(f"- {h}" for h in hallucinations)
        return (
            "다음 뉴스 기사를 요약해주세요.\n\n"
            f"{json.dumps(article, ensure_ascii=False, indent=2)}\n\n"
            "[이전 요약의 문제점 — 아래 내용은 원문에 없는 정보입니다. 반드시 제거하거나 수정하세요]\n"
            f"{issues}"
        )

    @staticmethod
    def _normalize_result_texts(result: dict[str, Any]) -> None:
        for field in ("headline_34", "headline_58", "headline_89", "summary"):
            value = result.get(field)
            if isinstance(value, str):
                result[field] = normalize_text(value)

    @staticmethod
    def _apply_length_checks(result: dict[str, Any]) -> None:
        result["_violations"] = []
        for field, (min_len, max_len) in {"headline_34": (29, 34), "headline_58": (50, 58), "headline_89": (76, 89)}.items():
            value = result.get(field, "")
            value_len = len(value)
            result[f"_{field}_len"] = value_len
            if value_len < min_len:
                result["_violations"].append(f"{field}:{value_len}<{min_len}")
            elif value_len > max_len:
                result["_violations"].append(f"{field}:{value_len}>{max_len}")

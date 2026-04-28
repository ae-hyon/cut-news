from __future__ import annotations

import sys
from typing import Any

from app.common.config import settings
from app.presentation.schemas import SummaryRequestSchema


class SummaryGatewayService:
    def _load_summary_modules(self) -> tuple[Any, Any, Any, Any]:
        path = str(settings.news_summarizer_dir.resolve())
        if path not in sys.path:
            sys.path.insert(0, path)

        from news_adapter import summarize_request
        from news_schema import NewsArticle, SummarizeRequest, SummarizerSettings

        return summarize_request, NewsArticle, SummarizeRequest, SummarizerSettings

    def _coerce_payload(self, payload: SummaryRequestSchema | dict) -> SummaryRequestSchema:
        if isinstance(payload, SummaryRequestSchema):
            return payload
        return SummaryRequestSchema.model_validate(payload)

    def _build_request(self, payload: SummaryRequestSchema, NewsArticle: Any, SummarizeRequest: Any) -> Any:
        article = NewsArticle.model_validate(payload.article.model_dump(mode='json', exclude_none=True))
        return SummarizeRequest(
            article=article,
            verify=payload.verify,
            max_retries=payload.max_retries,
        )

    def _build_runtime(self, payload: SummaryRequestSchema, SummarizerSettings: Any) -> Any:
        return SummarizerSettings(
            backend=payload.backend,
            model=payload.model,
            reasoning_effort=payload.reasoning_effort,
            timeout=payload.timeout,
        )

    def summarize(self, payload: Any) -> Any:
        normalized_payload = self._coerce_payload(payload)
        summarize_request, NewsArticle, SummarizeRequest, SummarizerSettings = self._load_summary_modules()
        request = self._build_request(normalized_payload, NewsArticle, SummarizeRequest)
        runtime = self._build_runtime(normalized_payload, SummarizerSettings)
        return summarize_request(request, runtime)

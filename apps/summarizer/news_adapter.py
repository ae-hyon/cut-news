from __future__ import annotations

from news_schema import SummarizeRequest, SummarizerSettings, SummaryResult, VerificationResult
from news_service import NewsSummarizer


def build_summarizer(settings: SummarizerSettings | None = None) -> NewsSummarizer:
    settings = settings or SummarizerSettings()
    return NewsSummarizer(
        backend=settings.backend,
        model=settings.model,
        reasoning_effort=settings.reasoning_effort,
        timeout=settings.timeout,
    )


def summarize_request(
    request: SummarizeRequest,
    settings: SummarizerSettings | None = None,
) -> SummaryResult:
    summarizer = build_summarizer(settings)
    return summarizer.summarize_model(
        request.article,
        verify=request.verify,
        max_retries=request.max_retries,
    )


def verify_request(article, summary, settings: SummarizerSettings | None = None) -> VerificationResult:
    summarizer = build_summarizer(settings)
    return summarizer.verify_model(article, summary)

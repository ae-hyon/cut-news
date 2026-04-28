from __future__ import annotations

import sys
import types
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.services.summary_service import SummaryGatewayService
from app.presentation.schemas import SummaryRequestSchema


class FakeNewsArticle(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str
    date: str | None = None
    author: str | None = None
    url: str | None = None
    content: str


class FakeSummarizeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    article: FakeNewsArticle
    verify: bool = False
    max_retries: int = 2


class FakeSummarizerSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')

    backend: str
    model: str
    reasoning_effort: str
    timeout: int


class FakeVerificationResult(BaseModel):
    verdict: str
    hallucinations: list[str]
    confidence: int


class FakeSummaryResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    headline_34: str
    headline_58: str
    headline_89: str
    summary: str
    verify: FakeVerificationResult = Field(alias='_verify')
    retry_count: int = Field(alias='_retry_count')
    violations: list[str] = Field(alias='_violations')
    headline_34_len: int = Field(alias='_headline_34_len')
    headline_58_len: int = Field(alias='_headline_58_len')
    headline_89_len: int = Field(alias='_headline_89_len')


class Capture:
    request = None
    runtime = None


def test_summary_gateway_accepts_api_schema_and_returns_typed_summary_result(monkeypatch):
    fake_schema = types.ModuleType('news_schema')
    fake_schema.NewsArticle = FakeNewsArticle
    fake_schema.SummarizeRequest = FakeSummarizeRequest
    fake_schema.SummarizerSettings = FakeSummarizerSettings
    fake_schema.SummaryResult = FakeSummaryResult

    expected = FakeSummaryResult(
        headline_34='요약 제목 길이 스물아홉자 이상 맞춤 결과',
        headline_58='요약 제목 오십자 이상 오십팔자 이하 길이 계약을 만족하는 결과입니다',
        headline_89='요약 제목은 칠십육자 이상 팔십구자 이하 길이 계약을 만족하도록 충분한 정보를 담아 작성한 테스트 결과입니다',
        summary='기사 요약 본문',
        _verify={'verdict': 'clean', 'hallucinations': [], 'confidence': 91},
        _retry_count=1,
        _violations=[],
        _headline_34_len=20,
        _headline_58_len=38,
        _headline_89_len=58,
    )

    def fake_summarize_request(request, runtime):
        Capture.request = request
        Capture.runtime = runtime
        return expected

    fake_adapter = types.ModuleType('news_adapter')
    fake_adapter.summarize_request = fake_summarize_request

    monkeypatch.setitem(sys.modules, 'news_schema', fake_schema)
    monkeypatch.setitem(sys.modules, 'news_adapter', fake_adapter)

    payload = SummaryRequestSchema.model_validate(
        {
            'article': {
                'title': '테스트 기사',
                'date': '2026-04-28',
                'author': '기자',
                'url': 'https://example.com/news/1',
                'content': '기사 본문',
            },
            'verify': True,
            'max_retries': 3,
            'backend': 'codex_exec',
            'model': 'gpt-5.4-mini',
            'reasoning_effort': 'low',
            'timeout': 123,
        }
    )

    result = SummaryGatewayService().summarize(payload)

    assert isinstance(Capture.request, FakeSummarizeRequest)
    assert isinstance(Capture.request.article, FakeNewsArticle)
    assert Capture.request.article.title == '테스트 기사'
    assert Capture.request.verify is True
    assert Capture.request.max_retries == 3

    assert isinstance(Capture.runtime, FakeSummarizerSettings)
    assert Capture.runtime.backend == 'codex_exec'
    assert Capture.runtime.model == 'gpt-5.4-mini'
    assert Capture.runtime.reasoning_effort == 'low'
    assert Capture.runtime.timeout == 123

    assert result is expected
    assert result.verify.verdict == 'clean'
    assert result.retry_count == 1
    assert result.summary == '기사 요약 본문'

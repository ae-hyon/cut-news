from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

HEADLINE_LIMITS = {
    "headline_34": (29, 34),
    "headline_58": (50, 58),
    "headline_89": (76, 89),
}


def normalize_text(value: str) -> str:
    return " ".join(value.split())


class NewsArticle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1)
    date: str | None = None
    author: str | None = None
    url: HttpUrl | None = None
    content: str = Field(min_length=1)


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Literal["clean", "suspicious", "skipped", "unknown"]
    hallucinations: list[str] = Field(default_factory=list)
    confidence: int = Field(ge=0, le=100)


class SummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    headline_34: str
    headline_58: str
    headline_89: str
    summary: str
    verify: VerificationResult = Field(alias="_verify")
    retry_count: int = Field(alias="_retry_count", ge=0)
    violations: list[str] = Field(alias="_violations", default_factory=list)
    headline_34_len: int = Field(alias="_headline_34_len", ge=0)
    headline_58_len: int = Field(alias="_headline_58_len", ge=0)
    headline_89_len: int = Field(alias="_headline_89_len", ge=0)

    @field_validator("headline_34")
    @classmethod
    def validate_headline_34(cls, value: str) -> str:
        value = normalize_text(value)
        min_len, max_len = HEADLINE_LIMITS["headline_34"]
        if not (min_len <= len(value) <= max_len):
            raise ValueError(f"headline_34 must be {min_len}~{max_len} chars")
        return value

    @field_validator("headline_58")
    @classmethod
    def validate_headline_58(cls, value: str) -> str:
        value = normalize_text(value)
        min_len, max_len = HEADLINE_LIMITS["headline_58"]
        if not (min_len <= len(value) <= max_len):
            raise ValueError(f"headline_58 must be {min_len}~{max_len} chars")
        return value

    @field_validator("headline_89")
    @classmethod
    def validate_headline_89(cls, value: str) -> str:
        value = normalize_text(value)
        min_len, max_len = HEADLINE_LIMITS["headline_89"]
        if not (min_len <= len(value) <= max_len):
            raise ValueError(f"headline_89 must be {min_len}~{max_len} chars")
        return value


class SummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article: NewsArticle
    verify: bool = False
    max_retries: int = Field(default=2, ge=0, le=5)


class SummarizerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    backend: Literal["codex_exec", "hermit_http", "hermes_cli"] = "codex_exec"
    model: str = "gpt-5.4-mini"
    reasoning_effort: str = "low"
    timeout: int = Field(default=300, ge=1, le=600)

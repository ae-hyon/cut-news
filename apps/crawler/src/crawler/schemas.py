from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CrawledArticle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    article_id: str | None = None
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    url: HttpUrl
    date: str | None = None
    author: str | None = None
    media: str | None = None
    content_source: str | None = None
    scraped_at: datetime | None = None

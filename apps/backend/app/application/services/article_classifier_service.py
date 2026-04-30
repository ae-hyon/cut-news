from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.application.services.article_ingest_service import ArticleClassificationDecision, ArticleClassifier
from app.common.config import Settings, settings

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _extract_json_object(text: str) -> str:
    cleaned = re.sub(r'\x08+', '', text).strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end < start:
        raise ValueError(f'Hermit CLI returned no JSON object: {cleaned!r}')
    return cleaned[start : end + 1]


class HermitCLIArticleClassifier:
    def __init__(
        self,
        *,
        command: str = 'hermit',
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        hermit_provider_name: str | None = 'z.ai',
        hermit_settings_path: Path | None = None,
        timeout: float = 60.0,
        runner: Runner = subprocess.run,
    ) -> None:
        self.command = command
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.hermit_provider_name = hermit_provider_name
        self.hermit_settings_path = hermit_settings_path or (Path.home() / '.hermit' / 'settings.json')
        self.timeout = timeout
        self.runner = runner

    def __call__(
        self,
        *,
        article_id: str,
        title: str,
        summary: str,
        content: str,
        original_url: str,
        raw_primary: str,
        raw_subcategory: str,
    ) -> ArticleClassificationDecision:
        prompt = self._build_prompt(
            article_id=article_id,
            title=title,
            summary=summary,
            content=content,
            original_url=original_url,
            raw_primary=raw_primary,
            raw_subcategory=raw_subcategory,
        )
        resolved = self._resolve_runtime()
        args = [
            'script',
            '-q',
            '/dev/null',
            self.command,
            prompt,
            '--base-url',
            resolved['base_url'],
            '--api-key',
            resolved['api_key'],
            '--model',
            resolved['model'],
            '--no-stream',
            '--dont-ask',
            '--max-turns',
            '1',
        ]

        result = self.runner(
            args,
            capture_output=True,
            text=True,
            check=True,
            timeout=self.timeout,
        )
        return ArticleClassificationDecision.model_validate_json(_extract_json_object(result.stdout))

    def _load_hermit_settings(self) -> dict[str, Any]:
        if not self.hermit_settings_path.exists():
            return {}
        return json.loads(self.hermit_settings_path.read_text(encoding='utf-8'))

    def _resolve_runtime(self) -> dict[str, str]:
        settings_payload = self._load_hermit_settings()
        providers = settings_payload.get('providers') or {}
        provider_payload = providers.get(self.hermit_provider_name or '') or {}

        base_url = self.base_url or provider_payload.get('base_url') or settings_payload.get('gateway_url')
        api_key = self.api_key or provider_payload.get('api_key') or settings_payload.get('gateway_api_key')
        model = self.model or settings_payload.get('model') or 'glm-5.1'

        if not base_url:
            raise ValueError('Hermit classifier could not resolve a base_url from config or ~/.hermit/settings.json')
        if not api_key:
            raise ValueError('Hermit classifier could not resolve an api_key from config or ~/.hermit/settings.json')
        return {
            'base_url': str(base_url).rstrip('/'),
            'api_key': str(api_key),
            'model': str(model),
        }

    def _build_prompt(
        self,
        *,
        article_id: str,
        title: str,
        summary: str,
        content: str,
        original_url: str,
        raw_primary: str,
        raw_subcategory: str,
    ) -> str:
        payload = {
            'article_id': article_id,
            'title': title,
            'summary': summary,
            'content': content[:4000],
            'original_url': original_url,
            'source_primary_category': raw_primary,
            'source_subcategory': raw_subcategory,
            'allowed_primary_categories': ['sectors', 'macro', 'assets', 'policy'],
            'allowed_subcategories': [
                'semiconductor',
                'mobility',
                'bio',
                'rates-fx',
                'energy',
                'supply-chain',
                'domestic-stocks',
                'global-stocks',
                'real-estate',
                'fiscal',
                'central-bank',
                'regulation',
            ],
        }
        return (
            'You classify Korean news articles for an economics news feed. '
            'Return only one JSON object with keys keep, primary_category, subcategory, confidence, reason. '
            'Set keep=false for non-economic or low-value articles. '
            'Confidence must be a number between 0 and 1. '
            f'Article payload: {json.dumps(payload, ensure_ascii=False)}'
        )


def build_article_classifier(config: Settings = settings) -> ArticleClassifier | None:
    if not config.article_classifier_enabled:
        return None
    if config.article_classifier_provider != 'hermit':
        return None
    return HermitCLIArticleClassifier(
        command=config.article_classifier_command,
        model=config.article_classifier_model,
        base_url=config.article_classifier_base_url,
        api_key=config.article_classifier_api_key,
        hermit_provider_name=config.article_classifier_hermit_provider_name,
        hermit_settings_path=config.article_classifier_hermit_settings_path,
        timeout=config.article_classifier_timeout_seconds,
    )

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.application.services.article_classifier_service import HermitCLIArticleClassifier, build_article_classifier
from app.application.services.article_ingest_service import ArticleClassificationDecision
from app.common.config import Settings


def test_hermit_cli_article_classifier_parses_structured_response(tmp_path: Path):
    captured_args: list[str] = []
    settings_path = tmp_path / 'settings.json'
    settings_path.write_text(
        json.dumps(
            {
                'providers': {
                    'z.ai': {
                        'base_url': 'https://api.z.ai/api/coding/paas/v4',
                        'api_key': 'zai-key',
                    }
                },
                'model': 'glm-5.1',
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    def runner(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        nonlocal captured_args
        captured_args = args
        assert kwargs['capture_output'] is True
        assert kwargs['text'] is True
        assert kwargs['check'] is True
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='^D\b\b{"keep": true, "primary_category": "macro", "subcategory": "supply-chain", "confidence": 0.91, "reason": "공급망 재편 기사"}\n',
            stderr='',
        )

    classifier = HermitCLIArticleClassifier(
        command='hermit',
        hermit_provider_name='z.ai',
        hermit_settings_path=settings_path,
        runner=runner,
    )

    decision = classifier(
        article_id='055',
        title='동남아 물류 재편에 해운 운임 변동성 확대',
        summary='동남아 생산기지 이동으로 공급망과 해운 운임 변동성이 커지고 있다.',
        content='동남아 생산기지 이전과 항만 적체 완화로 물류 경로가 재편되고 해운 운임 변동성이 커졌다는 분석이다.',
        original_url='https://example.com/economy/055',
        raw_primary='경제',
        raw_subcategory='일반',
    )

    assert captured_args[:4] == ['script', '-q', '/dev/null', 'hermit']
    assert '--base-url' in captured_args
    assert 'https://api.z.ai/api/coding/paas/v4' in captured_args
    assert '--api-key' in captured_args
    assert 'zai-key' in captured_args
    assert '--model' in captured_args
    assert 'glm-5.1' in captured_args
    assert decision == ArticleClassificationDecision(
        keep=True,
        primary_category='macro',
        subcategory='supply-chain',
        confidence=0.91,
        reason='공급망 재편 기사',
    )


def test_build_article_classifier_returns_hermit_cli_classifier_when_enabled(tmp_path: Path):
    settings = Settings(
        article_classifier_enabled=True,
        article_classifier_provider='hermit',
        article_classifier_command='hermit',
        article_classifier_model='glm-5.1',
        article_classifier_hermit_provider_name='z.ai',
        article_classifier_hermit_settings_path=tmp_path / 'settings.json',
    )

    classifier = build_article_classifier(settings)

    assert isinstance(classifier, HermitCLIArticleClassifier)

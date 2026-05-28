from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.services.article_ingest_service import _derive_categories


CASES = json.loads((Path(__file__).parent / 'fixtures' / 'article_classification_cases.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case', CASES, ids=[case['name'] for case in CASES])
def test_crawler_source_query_beats_broad_keyword_rules(case):
    derived = _derive_categories(case['article'], {})

    assert derived is not None
    assert derived.primary_category == case['expected_primary_category']
    assert derived.subcategory == case['expected_subcategory']
    assert derived.classification_source == case['expected_classification_source']

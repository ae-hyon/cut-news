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


def test_standalone_sports_match_word_does_not_fall_back_to_economy_macro():
    derived = _derive_categories(
        {
            'title': '울산 세계명문대학 조정 페스티벌 경기 개최',
            'content': '울산 태화강에서 대학 조정 선수단이 참가하는 문화·스포츠 행사가 열린다.',
        },
        {},
        '울산에서 대학 조정 선수단이 참가하는 페스티벌이 열린다.',
    )

    assert derived is None

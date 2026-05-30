from pipeline import step3_score


def test_step3_prompt_requests_llm_editorial_category_from_supported_taxonomy():
    system = step3_score.SYSTEM

    assert 'editorial_primary_category' in system
    assert 'editorial_subcategory' in system
    assert 'editorial_category_confidence' in system
    assert 'stock-domestic' in system
    assert 'economy-macro' in system
    assert 'tech-semiconductor' in system
    assert '기사 본문이 실제로 다루는 주제' in system

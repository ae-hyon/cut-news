from pipeline.step5_verify import SYSTEM


def test_step5_prompt_requires_topic_mismatch_detection_by_llm():
    assert "원문 제목과 본문이 다루는 핵심 사건·주제" in SYSTEM
    assert "관련기사·페이지 잡음·다른 사건" in SYSTEM
    assert "suspicious" in SYSTEM


def test_step5_prompt_uses_few_shot_boundary_examples_for_topic_judgment():
    assert "판정 예시" in SYSTEM
    assert "허웅 전 연인 명예훼손 재판" in SYSTEM
    assert "무인창고 현금 68억" in SYSTEM
    assert "부산 피란수도 유산" in SYSTEM
    assert "보은군" in SYSTEM
    assert "clean" in SYSTEM


def test_step5_prompt_keeps_expression_difference_allowance():
    assert "표현이 달라도 사실이 일치하면 할루시네이션이 아닙니다" in SYSTEM

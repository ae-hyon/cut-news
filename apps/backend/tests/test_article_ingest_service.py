from __future__ import annotations

import json
from pathlib import Path

from app.application.services.article_ingest_service import (
    ArticleClassificationDecision,
    load_summarized_articles,
    load_summarized_articles_report,
)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def test_load_summarized_articles_builds_backend_article_rows_from_summarizer_outputs(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {
            'title': '시장 금리 하락에 증권주 강세',
            'date': '2026-04-28',
            'author': '김기자',
            'url': 'https://example.com/economy/1',
            'content': '시장 금리가 하락하면서 증권주가 강세를 보였다는 본문입니다.',
        },
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', '_article_id': '001', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'scored' / '001.json', {'score': 82, '_article_id': '001'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    rows = load_summarized_articles(dataset)

    assert len(rows) == 1
    assert rows[0].id == 'SUM-001'
    assert rows[0].title == '시장 금리 하락에 증권주 강세'
    assert rows[0].summary == '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.'
    assert rows[0].content.startswith('시장 금리가 하락하면서')
    assert rows[0].primary_category == 'stock'
    assert rows[0].subcategory == 'stock-domestic'
    assert rows[0].published_at == '2026-04-28'
    assert rows[0].original_url == 'https://example.com/economy/1'
    assert rows[0].score_weight == 0.82


def test_load_summarized_articles_skips_items_without_summary(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '제목', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문'},
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', '_article_id': '001', '_title': '제목'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_skips_items_without_clean_verification(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '제목', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '제목',
            'headline_58': '제목',
            'headline_89': '제목',
            'summary': '요약',
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'suspicious', '_article_id': '001', '_title': '제목'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_defaults_score_weight_when_scored_output_is_missing(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '제목', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '제목',
            'headline_58': '제목',
            'headline_89': '제목',
            'summary': '요약',
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', '_article_id': '001', '_title': '제목'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    rows = load_summarized_articles(dataset)

    assert len(rows) == 1
    assert rows[0].score_weight == 1.0


def test_load_summarized_articles_skips_political_article_without_economic_title_signal(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '003.json',
        {
            'title': "李대통령, 순방 마치고 서울 도착…'중동 리스크' 대응 전념",
            'date': '2026-04-24',
            'author': '황윤기, 임형섭',
            'url': 'https://example.com/politics/003',
            'content': '대통령 순방과 외교 대응을 설명하는 본문이다. 에너지와 코스피 언급이 일부 포함돼도 경제 기사 자체는 아니다.',
        },
    )
    write_json(
        dataset / 'summarized' / '003.json',
        {
            'headline_34': "이재명 대통령, 순방 마치고 귀국",
            'headline_58': '이재명 대통령이 순방을 마치고 귀국해 중동 리스크 대응에 전념한다',
            'headline_89': '이재명 대통령이 인도·베트남 순방을 마치고 귀국해 중동 리스크 대응과 외교 현안 점검에 나선다',
            'summary': '이재명 대통령이 순방을 마치고 귀국해 외교 현안 대응에 나선다.',
        },
    )
    write_json(dataset / 'verified' / '003.json', {'verdict': 'clean', '_article_id': '003', '_title': '이재명 대통령, 순방 마치고 귀국'})
    write_json(dataset / 'category_map.json', [{'article_id': '003', 'primary_category': '정치', 'subcategory': '대통령실'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_skips_entertainment_article_without_economic_title_signal(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '048.json',
        {
            'title': "[가요소식] 트와이스, 북미 투어로 55만명 동원 '자체 최다 규모'",
            'date': '2026-04-24',
            'author': '김선우',
            'url': 'https://example.com/entertainment/048',
            'content': '트와이스와 엔하이픈 공연 소식을 전하는 기사 본문이다.',
        },
    )
    write_json(
        dataset / 'summarized' / '048.json',
        {
            'headline_34': '트와이스 북미 투어 55만명 동원',
            'headline_58': '트와이스가 북미 투어 35회 공연으로 55만명을 동원했다',
            'headline_89': '트와이스가 북미 20개 도시 35회 공연으로 55만명을 동원하며 자체 최다 규모 투어 기록을 세웠다',
            'summary': '트와이스가 북미 투어에서 55만명을 동원했다.',
        },
    )
    write_json(dataset / 'verified' / '048.json', {'verdict': 'clean', '_article_id': '048', '_title': '트와이스 북미 투어 55만명 동원'})
    write_json(dataset / 'category_map.json', [{'article_id': '048', 'primary_category': '문화연예', 'subcategory': '가요'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_prefers_trade_category_map_over_loose_energy_keyword_hit(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '019.json',
        {
            'title': '파라과이 통해 중남미 진출 도모…아순시온서 한국 상품전시회',
            'date': '2026-04-24',
            'author': '강성철',
            'url': 'https://example.com/economy/019',
            'content': '중남미 시장 진출과 바이어 매칭, 수출 확대를 다루는 기사다. 본문 후반에 에너지 제품 수요 언급이 일부 포함된다.',
        },
    )
    write_json(
        dataset / 'summarized' / '019.json',
        {
            'headline_34': '파라과이서 한국 상품전시회 개최',
            'headline_58': '파라과이에서 한국 상품전시회와 바이어 매칭 행사가 열렸다',
            'headline_89': '파라과이 아순시온에서 한국 상품전시회와 바이어 매칭 행사가 열려 중남미 시장 진출 확대를 모색했다',
            'summary': '파라과이에서 한국 상품전시회와 바이어 매칭 행사가 열렸다.',
        },
    )
    write_json(dataset / 'verified' / '019.json', {'verdict': 'clean', '_article_id': '019', '_title': '파라과이서 한국 상품전시회 개최'})
    write_json(dataset / 'category_map.json', [{'article_id': '019', 'primary_category': '경제', 'subcategory': '무역'}])

    rows = load_summarized_articles(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'economy'
    assert rows[0].subcategory == 'economy-trade'


def test_load_summarized_articles_skips_economy_it_snapshot_without_market_or_industry_signal(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '049.json',
        {
            'title': '[테크스냅] SKB, 도림천서 환경 정화 봉사활동',
            'date': '2026-04-24',
            'author': '유현민',
            'url': 'https://example.com/economy/049',
            'content': 'SK브로드밴드가 ESG 경영의 일환으로 임직원 봉사활동을 진행했다.',
        },
    )
    write_json(
        dataset / 'summarized' / '049.json',
        {
            'headline_34': 'SKB, 도림천서 환경 정화 봉사활동',
            'headline_58': 'SK브로드밴드가 도림천 일대에서 환경 정화 봉사활동을 진행했다',
            'headline_89': 'SK브로드밴드가 ESG 경영의 일환으로 도림천 일대에서 임직원 환경 정화 봉사활동을 진행했다',
            'summary': 'SK브로드밴드가 환경 정화 봉사활동을 진행했다.',
        },
    )
    write_json(dataset / 'verified' / '049.json', {'verdict': 'clean', '_article_id': '049', '_title': 'SKB, 도림천서 환경 정화 봉사활동'})
    write_json(dataset / 'category_map.json', [{'article_id': '049', 'primary_category': '경제', 'subcategory': 'IT통신'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_skips_social_accident_article_even_if_title_mentions_gas(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '029.json',
        {
            'title': '청주 호텔 지하주차장서 가스계 소화설비 오작동…2명 부상',
            'date': '2026-04-24',
            'author': '천경환',
            'url': 'https://example.com/social/029',
            'content': '지하주차장 소화설비 오작동으로 이산화탄소가 방출돼 부상자가 발생한 사고 기사다.',
        },
    )
    write_json(
        dataset / 'summarized' / '029.json',
        {
            'headline_34': '청주 호텔 지하주차장 소화설비 오작동',
            'headline_58': '청주 호텔 지하주차장에서 가스계 소화설비 오작동으로 2명이 다쳤다',
            'headline_89': '청주 호텔 지하주차장에서 가스계 소화설비가 오작동해 이산화탄소가 방출되며 2명이 다쳤다',
            'summary': '청주 호텔 지하주차장에서 소화설비 오작동으로 2명이 다쳤다.',
        },
    )
    write_json(dataset / 'verified' / '029.json', {'verdict': 'clean', '_article_id': '029', '_title': '청주 호텔 지하주차장 소화설비 오작동'})
    write_json(dataset / 'category_map.json', [{'article_id': '029', 'primary_category': '사회', 'subcategory': '사건사고'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_uses_classifier_fallback_for_ambiguous_economic_article(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '055.json',
        {
            'title': '동남아 물류 재편에 해운 운임 변동성 확대',
            'date': '2026-04-24',
            'author': '최기자',
            'url': 'https://example.com/economy/055',
            'content': '동남아 생산기지 이전과 항만 적체 완화로 물류 경로가 재편되고 해운 운임 변동성이 커졌다는 분석이다.',
        },
    )
    write_json(
        dataset / 'summarized' / '055.json',
        {
            'headline_34': '동남아 물류 재편에 해운 운임 변동성 확대',
            'headline_58': '동남아 생산기지 이동으로 해운 운임 변동성이 커지고 있다',
            'headline_89': '동남아 생산기지 이동과 항만 적체 완화로 해운 운임 변동성이 커지며 공급망 재편 압력이 확대되고 있다',
            'summary': '동남아 생산기지 이동으로 공급망과 해운 운임 변동성이 커지고 있다.',
        },
    )
    write_json(dataset / 'verified' / '055.json', {'verdict': 'clean', '_article_id': '055', '_title': '동남아 물류 재편에 해운 운임 변동성 확대'})
    write_json(dataset / 'category_map.json', [{'article_id': '055', 'primary_category': '경제', 'subcategory': '일반'}])

    calls: list[tuple[str, str]] = []

    def classifier(*, article_id: str, title: str, summary: str, **_kwargs) -> ArticleClassificationDecision:
        calls.append((article_id, title))
        assert summary == '동남아 생산기지 이동으로 공급망과 해운 운임 변동성이 커지고 있다.'
        return ArticleClassificationDecision(
            keep=True,
            primary_category='economy',
            subcategory='economy-trade',
            confidence=0.92,
            reason='공급망/해운 운임 기사',
        )

    rows = load_summarized_articles(dataset, classifier=classifier)

    assert calls == [('055', '동남아 물류 재편에 해운 운임 변동성 확대')]
    assert len(rows) == 1
    assert rows[0].primary_category == 'economy'
    assert rows[0].subcategory == 'economy-trade'


def test_load_summarized_articles_reuses_cached_classifier_result_without_recalling_classifier(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '056.json',
        {
            'title': '새로운 경영 지표 놓고 기업 대응 분주',
            'date': '2026-04-24',
            'author': '박기자',
            'url': 'https://example.com/economy/056',
            'content': '기업들이 새로운 경영 지표와 외부 환경 변화에 대응하고 있다는 기사다.',
        },
    )
    write_json(
        dataset / 'summarized' / '056.json',
        {
            'headline_34': '새로운 경영 지표 놓고 기업 대응 분주',
            'headline_58': '기업들이 새로운 경영 지표와 환경 변화에 대응하고 있다',
            'headline_89': '기업들이 새로운 경영 지표와 외부 환경 변화에 맞춰 사업 전략을 재조정하고 있다',
            'summary': '기업들이 새로운 경영 지표와 환경 변화에 대응하고 있다.',
        },
    )
    write_json(dataset / 'verified' / '056.json', {'verdict': 'clean', '_article_id': '056', '_title': '새로운 경영 지표 놓고 기업 대응 분주'})
    write_json(dataset / 'category_map.json', [{'article_id': '056', 'primary_category': '경제', 'subcategory': '일반'}])

    call_count = 0

    def classifier(**_kwargs) -> ArticleClassificationDecision:
        nonlocal call_count
        call_count += 1
        return ArticleClassificationDecision(
            keep=True,
            primary_category='economy',
            subcategory='economy-trade',
            confidence=0.88,
            reason='공급망 기사',
        )

    first_rows = load_summarized_articles(dataset, classifier=classifier)
    second_rows = load_summarized_articles(dataset, classifier=classifier)

    assert len(first_rows) == 1
    assert len(second_rows) == 1
    assert call_count == 1


def test_load_summarized_articles_skips_low_confidence_clean_verification(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '시장 금리 하락에 증권주 강세', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', 'confidence': 61, '_article_id': '001', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_skips_summary_with_validation_violations(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '시장 금리 하락에 증권주 강세', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '시장 금리가 하락하면서 증권주가 강세를 보였다는 본문입니다.'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
            '_violations': ['headline_34 too short'],
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', 'confidence': 95, '_article_id': '001', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_requires_stricter_confidence_for_description_fallback_articles(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '시장 금리 하락에 증권주 강세', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문', 'content_source': 'description'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', 'confidence': 84, '_article_id': '001', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_skips_summary_after_too_many_retries(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '시장 금리 하락에 증권주 강세', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '시장 금리가 하락하면서 증권주가 강세를 보였다는 본문입니다.'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
            '_retry_count': 3,
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', 'confidence': 95, '_article_id': '001', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_load_summarized_articles_report_tracks_quality_gate_skips_and_classification_provenance(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '시장 금리 하락에 증권주 강세', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문'},
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
        },
    )
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', 'confidence': 61, '_article_id': '001', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    write_json(
        dataset / 'json' / '002.json',
        {'title': '동남아 물류 재편에 해운 운임 변동성 확대', 'date': '2026-04-28', 'url': 'https://example.com/2', 'content': '동남아 생산기지 이동과 항만 적체 완화로 해운 운임 변동성이 커지고 있다.'},
    )
    write_json(
        dataset / 'summarized' / '002.json',
        {
            'headline_34': '동남아 물류 재편에 해운 운임 변동성 확대',
            'headline_58': '동남아 생산기지 이동으로 해운 운임 변동성이 커지고 있다',
            'headline_89': '동남아 생산기지 이동과 항만 적체 완화로 해운 운임 변동성이 커지며 공급망 재편 압력이 확대되고 있다',
            'summary': '동남아 생산기지 이동으로 공급망과 해운 운임 변동성이 커지고 있다.',
        },
    )
    write_json(dataset / 'verified' / '002.json', {'verdict': 'clean', 'confidence': 96, '_article_id': '002', '_title': '동남아 물류 재편에 해운 운임 변동성 확대'})
    write_json(dataset / 'category_map.json', [
        {'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'},
        {'article_id': '002', 'primary_category': '경제', 'subcategory': '일반'},
    ])

    def classifier(**_kwargs) -> ArticleClassificationDecision:
        return ArticleClassificationDecision(
            keep=True,
            primary_category='economy',
            subcategory='economy-trade',
            confidence=0.92,
            reason='공급망 기사',
        )

    rows, report = load_summarized_articles_report(dataset, classifier=classifier)

    assert len(rows) == 1
    assert rows[0].id == 'SUM-002'
    assert report['quality_gate_skip_counts'] == {'low_confidence': 1}
    assert report['classification_source_counts'] == {'classifier_fallback': 1}
    assert report['dropped_reason_counts'] == {'quality_gate_low_confidence': 1}


def test_repo_summarizer_dataset_maps_to_supported_backend_categories():
    rows = load_summarized_articles(Path(__file__).resolve().parents[2] / 'summarizer' / 'data')

    supported = {
        'stock': {'stock-domestic', 'stock-overseas', 'stock-etf', 'stock-unlisted'},
        'crypto': {'crypto-bitcoin', 'crypto-altcoin', 'crypto-defi', 'crypto-nft'},
        'realestate': {'realestate-apt', 'realestate-subscription', 'realestate-lease', 'realestate-commercial'},
        'politics': {'politics-domestic', 'politics-diplomacy', 'politics-policy'},
        'economy': {'economy-macro', 'economy-finance', 'economy-trade'},
        'tech': {'tech-ai', 'tech-semiconductor', 'tech-startup', 'tech-bigtech'},
        'entertainment': {'entertainment-kpop', 'entertainment-drama', 'entertainment-movie'},
        'sports': {'sports-soccer', 'sports-baseball', 'sports-basketball', 'sports-esports'},
        'global': {'global-us', 'global-china', 'global-europe', 'global-asia'},
        'lifestyle': {'lifestyle-health', 'lifestyle-travel', 'lifestyle-food'},
    }
    for row in rows:
        assert row.primary_category in supported
        assert row.subcategory in supported[row.primary_category]

from __future__ import annotations

import json
from pathlib import Path

from app.application.services.article_ingest_service import (
    _summary_topic_mismatch,
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


def test_load_summarized_articles_uses_crawler_source_query_when_category_map_is_absent(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / 'stock-001.json',
        {
            'title': '일반 시장 소식',
            'date': '2026-04-28',
            'url': 'https://example.com/stock/1',
            'content': '국내주식 시장을 다루는 기사처럼 수집 쿼리의 서비스 카테고리를 보존해야 합니다.',
            'source_category': 'stock',
            'source_query': '국내주식',
        },
    )
    write_json(
        dataset / 'summarized' / 'stock-001.json',
        {
            'headline_34': '일반 시장 소식',
            'headline_58': '일반 시장 소식',
            'headline_89': '일반 시장 소식',
            'summary': '국내주식 수집 카테고리 기반 분류 확인용 요약입니다.',
        },
    )
    write_json(dataset / 'verified' / 'stock-001.json', {'verdict': 'clean', '_article_id': 'stock-001', '_title': '일반 시장 소식'})

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'stock'
    assert rows[0].subcategory == 'stock-domestic'
    assert report['classification_source_counts'] == {'crawler_source_query': 1}


def test_load_summarized_articles_prefers_llm_editorial_category_over_keyword_rules(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / 'samsung-pay-001.json',
        {
            'title': '삼성전자 성과급 3년 131조 추산…주주 환원 잠식 우려 확대',
            'date': '2026-05-29',
            'url': 'https://example.com/economy/samsung-pay',
            'content': '삼성전자 노사 성과급 합의 적용 시 지급 총액이 131조 원으로 예상되고 주주 환원 잠식 우려가 제기됐다.',
            'source_category': 'economy',
            'source_query': '거시경제',
        },
    )
    write_json(
        dataset / 'summarized' / 'samsung-pay-001.json',
        {
            'headline_34': '삼성전자 성과급 3년 131조 원 추산·주주환원 우려',
            'summary': '삼성전자 성과급 합의가 주주 환원을 잠식할 수 있다는 우려가 제기됐습니다.',
        },
    )
    write_json(dataset / 'verified' / 'samsung-pay-001.json', {'verdict': 'clean', 'confidence': 98})
    write_json(
        dataset / 'scored' / 'samsung-pay-001.json',
        {
            'score': 78,
            '_article_id': 'samsung-pay-001',
            'editorial_primary_category': 'economy',
            'editorial_subcategory': 'economy-macro',
            'editorial_category_confidence': 92,
            'editorial_category_reason': '기업 임금·주주환원에 미치는 거시 경제 이슈',
        },
    )

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'economy'
    assert rows[0].subcategory == 'economy-macro'
    assert report['classification_source_counts'] == {'editorial_category': 1}


def test_load_summarized_articles_ignores_low_confidence_editorial_category(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / 'ai-001.json',
        {
            'title': 'ETRI, K-피지컬 AI 전략 첫 공개·로봇지능 연구 집중',
            'date': '2026-05-28',
            'url': 'https://example.com/ai/1',
            'content': 'ETRI는 피지컬 AI 시대 전략을 공개하고 AI 로봇 생태계를 핵심 전략으로 제시했다.',
        },
    )
    write_json(dataset / 'summarized' / 'ai-001.json', {'headline_34': 'ETRI, K-피지컬 AI 전략 첫 공개', 'summary': 'ETRI가 피지컬 AI 전략을 공개했습니다.'})
    write_json(dataset / 'verified' / 'ai-001.json', {'verdict': 'clean', 'confidence': 96})
    write_json(
        dataset / 'scored' / 'ai-001.json',
        {
            'score': 80,
            'editorial_primary_category': 'global',
            'editorial_subcategory': 'global-china',
            'editorial_category_confidence': 40,
        },
    )

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'tech'
    assert rows[0].subcategory == 'tech-ai'
    assert report['classification_source_counts'] == {'keyword_rule': 1}


def test_load_summarized_articles_prefers_text_signal_over_mismatched_crawler_source_query(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / 'ai-001.json',
        {
            'title': 'ETRI, K-피지컬 AI 전략 첫 공개·로봇지능 연구 집중',
            'date': '2026-05-28',
            'url': 'https://example.com/ai/1',
            'content': 'ETRI는 피지컬 AI 시대 전략을 공개하고 AI 로봇 생태계를 핵심 전략으로 제시했다.',
            'source_category': 'global',
            'source_query': '중국',
        },
    )
    write_json(dataset / 'summarized' / 'ai-001.json', {'headline_34': 'ETRI, K-피지컬 AI 전략 첫 공개', 'summary': 'ETRI가 피지컬 AI 전략을 공개했습니다.'})
    write_json(dataset / 'verified' / 'ai-001.json', {'verdict': 'clean', 'confidence': 96})

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'tech'
    assert rows[0].subcategory == 'tech-ai'
    assert report['classification_source_counts'] == {'keyword_rule': 1}


def test_load_summarized_articles_drops_mismatched_crawler_source_query_without_text_signal(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / 'realestate-001.json',
        {
            'title': '공정위, 중고 아이폰몰 6억 피해·대표 안모 씨 검찰 고발',
            'date': '2026-05-28',
            'url': 'https://example.com/consumer/1',
            'content': '공정거래위원회가 중고 아이폰 판매 업체에 제재를 내리고 대표를 검찰에 고발했다. 관련 기사 목록에는 청약과 주가 뉴스도 함께 노출된다.',
            'source_category': 'realestate',
            'source_query': '청약',
        },
    )
    write_json(dataset / 'summarized' / 'realestate-001.json', {'headline_34': '공정위, 중고 아이폰몰 피해 제재', 'summary': '공정위가 중고 아이폰몰 피해 건을 제재했습니다.'})
    write_json(dataset / 'verified' / 'realestate-001.json', {'verdict': 'clean', 'confidence': 96})

    rows, report = load_summarized_articles_report(dataset)

    assert rows == []
    assert report['drop_reason_counts'] == {'category_unmapped': 1}


def test_load_summarized_articles_keeps_tax_policy_article_without_noisy_content_stock_match(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / 'policy-001.json',
        {
            'title': '가상자산 소득세 2027년 시행 앞두고 폐지론·혼란 심화',
            'date': '2026-05-28',
            'url': 'https://example.com/policy/1',
            'content': '가상자산 과세 논란을 다루는 본문이다. 관련 기사 영역에는 증권과 미국 뉴스 링크가 섞여 있다.',
            'source_category': 'politics',
            'source_query': '국내정치',
        },
    )
    write_json(
        dataset / 'summarized' / 'policy-001.json',
        {
            'headline_34': '가상자산 소득세 시행 앞두고 혼란',
            'summary': '가상자산 소득세 시행을 앞두고 폐지론이 커지고 국세청은 과세 시스템 준비를 이어가고 있습니다.',
        },
    )
    write_json(dataset / 'verified' / 'policy-001.json', {'verdict': 'clean', 'confidence': 96})

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'politics'
    assert rows[0].subcategory == 'politics-policy'
    assert report['classification_source_counts'] == {'keyword_rule': 1}


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


def test_load_summarized_articles_maps_medical_reproductive_health_to_lifestyle_health(tmp_path: Path):
    dataset = tmp_path
    write_json(dataset / 'json' / 'health-001.json', {
        'title': '여성호르몬 노출 기간 짧을수록 폐경 후 심부전 위험↑',
        'date': '2026-05-29',
        'url': 'https://example.com/health-001',
        'content': '폐경 여성 연구에서 여성호르몬 노출 기간과 심부전 위험의 연관성이 확인됐다.',
        'source_category': 'global',
        'source_query': '아시아',
    })
    write_json(dataset / 'summarized' / 'health-001.json', {
        'headline_34': '여성호르몬 노출 짧을수록 심부전 위험 증가',
        'headline_58': '폐경 여성 369만명 추적 결과 호르몬 노출 기간 짧을수록 심부전 위험 증가',
        'headline_89': '폐경 여성 369만명 추적 분석에서 여성호르몬 노출 기간이 짧을수록 심부전 위험이 높아지는 경향이 확인됐다',
        'summary': '폐경 여성 369만명을 약 10년 추적한 연구에서 여성호르몬 노출 기간이 짧을수록 심부전 위험이 높아졌습니다.',
    })
    write_json(dataset / 'verified' / 'health-001.json', {'verdict': 'clean', 'confidence': 96})

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].primary_category == 'lifestyle'
    assert rows[0].subcategory == 'lifestyle-health'
    assert report['classification_source_counts'] == {'keyword_rule': 1}



def test_load_summarized_articles_report_ignores_unselected_json_when_selection_manifest_exists(tmp_path: Path):
    dataset = tmp_path
    write_json(dataset / 'json' / 'selected.json', {'title': '시장 금리 하락에 증권주 강세', 'date': '2026-04-28', 'url': 'https://example.com/selected', 'content': '시장 금리 하락 영향으로 증권주가 강세를 보였다.'})
    write_json(dataset / 'json' / 'unselected.json', {'title': '낮은 점수 기사', 'date': '2026-04-28', 'url': 'https://example.com/unselected', 'content': '낮은 점수 기사 본문'})
    write_json(dataset / 'summary_selection.json', {'selected_article_ids': ['selected'], 'selected_count': 1, 'total_json_count': 2})
    write_json(dataset / 'summarized' / 'selected.json', {
        'headline_34': '시장 금리 하락에 증권주 강세',
        'headline_58': '시장 금리 하락으로 증권주가 일제히 강세를 보였다',
        'headline_89': '시장 금리 하락으로 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
        'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
    })
    write_json(dataset / 'verified' / 'selected.json', {'verdict': 'clean', 'confidence': 96, '_article_id': 'selected', '_title': '시장 금리 하락에 증권주 강세'})
    write_json(dataset / 'category_map.json', [{'article_id': 'selected', 'primary_category': '경제', 'subcategory': '증권'}])

    rows, report = load_summarized_articles_report(dataset)

    assert [row.id for row in rows] == ['SUM-selected']
    assert report['drop_reason_counts'] == {}



def test_summary_topic_mismatch_allows_korean_particle_and_compound_overlap():
    assert not _summary_topic_mismatch(
        {'title': '17세 소년병 잠든 세계 유일 유엔묘지…‘세계유산’ 없는 부산의 도전'},
        {
            'headline_34': '부산 피란수도 유산 11곳, 2030년 세계유산 등재 도전',
            'headline_58': '부산 피란수도 유산 11곳이 2030년 세계유산 등재에 도전한다',
            'headline_89': '부산 피란수도 유산 11곳은 예비평가를 거쳐 2030년 세계유산 등재를 목표로 한다',
            'summary': '부산시는 유엔기념공원 등 한국전쟁기 피란수도 부산의 11개 유산을 유네스코 세계유산으로 등재하는 절차를 추진하고 있습니다.',
        },
    )
    assert not _summary_topic_mismatch(
        {'title': '"전국 축구 원로들 한자리에"…보은서 김용식배 축구대회'},
        {
            'headline_34': '보은 4개 축구장서 23회 김용식배…19개 시도 22팀 참가',
            'headline_58': '보은군 4개 축구장에서 김용식배 축구대회가 열린다',
            'headline_89': '보은군에서 김용식배 축구대회가 열리며 전국 시도 지회 22개 팀이 참가한다',
            'summary': '30~31일 충북 보은군에서 23회 김용식배 축구대회가 공설운동장 등 4개 축구장에서 열립니다.',
        },
    )


def test_summary_topic_mismatch_still_rejects_late_title_term_padding():
    assert _summary_topic_mismatch(
        {'title': '농구 허웅 전 연인 명예훼손 재판'},
        {
            'headline_34': '무인창고 현금 68억 은닉·허웅 명예훼손 재판',
            'headline_58': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐다',
            'headline_89': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐고 관계자 조사가 이어지고 있다',
            'summary': '무인창고 현금 은닉 사건 수사가 확대됐다는 내용입니다.',
        },
    )


def test_load_summarized_articles_report_tracks_quality_gate_skips(tmp_path: Path):
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
        {'title': '동남아 물류 재편에 해운 운임 변동성 확대', 'date': '2026-04-28', 'url': 'https://example.com/2', 'content': '동남아 생산기지 이동과 항만 적체 완화로 공급망과 해운 운임 변동성이 커지고 있다.'},
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

    write_json(
        dataset / 'json' / '003.json',
        {
            'title': '농구 허웅 전 연인 명예훼손 재판',
            'date': '2026-04-28',
            'url': 'https://example.com/3',
            'content': '허웅 전 연인의 명예훼손 재판 절차를 다룬 기사 본문입니다.',
        },
    )
    write_json(
        dataset / 'summarized' / '003.json',
        {
            'headline_34': '무인창고 현금 68억 은닉·허웅 명예훼손 재판',
            'headline_58': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐다',
            'headline_89': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐고 관계자 조사가 이어지고 있다',
            'summary': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐습니다.',
        },
    )
    write_json(dataset / 'verified' / '003.json', {'verdict': 'suspicious', 'confidence': 97, 'hallucinations': ['요약문이 원문 제목의 허웅 재판이 아니라 무인창고 현금 은닉 사건을 중심으로 작성됨'], '_article_id': '003', '_title': '농구 허웅 전 연인 명예훼손 재판'})
    write_json(dataset / 'category_map.json', [
        {'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'},
        {'article_id': '002', 'primary_category': '경제', 'subcategory': '일반'},
        {'article_id': '003', 'primary_category': '스포츠', 'subcategory': '농구'},
    ])

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].id == 'SUM-002'
    assert report['quality_gate_skip_counts'] == {'low_confidence': 1, 'verdict_not_clean': 1}
    assert report['drop_reason_counts']['quality_gate:verdict_not_clean'] == 1


def test_load_summarized_articles_does_not_hard_drop_clean_verifier_on_topic_overlap_heuristic(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '003.json',
        {
            'title': '농구 허웅 전 연인 명예훼손 재판',
            'date': '2026-04-28',
            'url': 'https://example.com/3',
            'content': '허웅 전 연인의 명예훼손 재판 절차를 다룬 기사 본문입니다.',
        },
    )
    write_json(
        dataset / 'summarized' / '003.json',
        {
            'headline_34': '무인창고 현금 68억 은닉·허웅 명예훼손 재판',
            'headline_58': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐다',
            'headline_89': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐고 관계자 조사가 이어지고 있다',
            'summary': '무인창고에서 현금 68억 원이 발견되며 자금 은닉 수사가 확대됐습니다.',
        },
    )
    write_json(dataset / 'verified' / '003.json', {'verdict': 'clean', 'confidence': 97, '_article_id': '003', '_title': '농구 허웅 전 연인 명예훼손 재판'})
    write_json(
        dataset / 'scored' / '003.json',
        {
            'score': 72,
            'editorial_primary_category': 'sports',
            'editorial_subcategory': 'sports-basketball',
            'editorial_category_confidence': 90,
            'editorial_category_reason': '농구 선수 관련 재판 기사',
        },
    )
    write_json(dataset / 'category_map.json', [
        {'article_id': '003', 'primary_category': '스포츠', 'subcategory': '농구'},
    ])

    rows, report = load_summarized_articles_report(dataset)

    assert len(rows) == 1
    assert rows[0].id == 'SUM-003'
    assert report['quality_gate_skip_counts'] == {}
    assert report['drop_reason_counts'] == {}



def test_load_summarized_articles_report_tracks_import_drop_reasons_and_classification_sources(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {
            'title': '시장 금리 하락에 증권주 강세',
            'date': '2026-04-28',
            'url': 'https://example.com/1',
            'content': '시장 금리 하락과 증권 업종 흐름을 다룬 본문입니다.',
        },
    )
    write_json(dataset / 'summarized' / '001.json', {'headline_34': '시장 금리 하락에 증권주 강세', 'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.'})
    write_json(dataset / 'verified' / '001.json', {'verdict': 'clean', 'confidence': 96})

    write_json(
        dataset / 'json' / '002.json',
        {
            'title': '코스피 상승에 투자 심리 회복',
            'date': '2026-04-28',
            'url': 'https://example.com/2',
            'content': '코스피 상승과 투자 심리 회복을 다룬 본문입니다.',
        },
    )
    write_json(dataset / 'summarized' / '002.json', {'headline_34': '코스피 상승에 투자 심리 회복', 'summary': '코스피 상승으로 투자 심리가 회복됐습니다.'})
    write_json(dataset / 'verified' / '002.json', {'verdict': 'clean', 'confidence': 96})

    write_json(
        dataset / 'json' / '003.json',
        {
            'title': '지역 축제 관람객 증가',
            'date': '2026-04-28',
            'url': 'https://example.com/3',
            'content': '지역 축제 관람객이 증가했다는 본문입니다.',
        },
    )
    write_json(dataset / 'summarized' / '003.json', {'headline_34': '지역 축제 관람객 증가', 'summary': '지역 축제 관람객이 증가했습니다.'})
    write_json(dataset / 'verified' / '003.json', {'verdict': 'clean', 'confidence': 96})

    write_json(
        dataset / 'json' / '004.json',
        {
            'title': 'AI 반도체 수요 확대',
            'date': '2026-04-28',
            'url': 'https://example.com/4',
            'content': 'AI 반도체 수요 확대를 다룬 본문입니다.',
        },
    )
    write_json(dataset / 'summarized' / '004_error.json', {'error': 'summary contract violation', '_article_id': '004'})

    write_json(
        dataset / 'json' / '005.json',
        {
            'title': '전기차 배터리 공급망 재편',
            'date': '2026-04-28',
            'url': 'https://example.com/5',
            'content': '전기차 배터리 공급망 재편을 다룬 본문입니다.',
        },
    )
    write_json(dataset / 'summarized' / '005.json', {'headline_34': '전기차 배터리 공급망 재편', 'summary': '전기차 배터리 공급망이 재편되고 있습니다.'})
    write_json(dataset / 'verified' / '005_error.json', {'error': 'verification failure', '_article_id': '005'})

    write_json(
        dataset / 'category_map.json',
        [
            {'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'},
            {'article_id': '002', 'primary_category': '경제', 'subcategory': '일반'},
            {'article_id': '003', 'primary_category': '경제', 'subcategory': '일반'},
        ],
    )

    rows, report = load_summarized_articles_report(dataset)

    assert [row.id for row in rows] == ['SUM-001', 'SUM-002']
    assert report['classification_source_counts'] == {
        'source_subcategory': 1,
        'keyword_rule': 1,
    }
    assert report['drop_reason_counts'] == {
        'category_unmapped': 1,
        'summary_error': 1,
        'verification_error': 1,
    }


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

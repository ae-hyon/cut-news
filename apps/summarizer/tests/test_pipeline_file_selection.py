import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import step3_score, step4_summarize, step5_verify


def _write_json(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'ok': True}), encoding='utf-8')


def test_step3_selects_hash_article_ids_and_skips_error_files(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    _write_json(json_dir / '05d506932773.json')
    _write_json(json_dir / 'a6a3cbbe2ed1.json')
    _write_json(json_dir / 'a6a3cbbe2ed1_error.json')
    monkeypatch.setattr(step3_score, 'JSON_DIR', json_dir)

    assert [p.name for p in step3_score._input_json_files()] == [
        '05d506932773.json',
        'a6a3cbbe2ed1.json',
    ]


def test_step3_preserves_crawler_category_metadata_in_score_output(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    scored_dir = tmp_path / 'scored'
    _write_json(json_dir / 'tech-article.json')
    article = {
        'title': 'AI 전략 발표',
        'date': '2026-05-29',
        'content': '정부와 연구기관이 피지컬 AI 전략을 발표했다.',
        'source_category': 'tech',
        'source_query': 'AI',
    }
    (json_dir / 'tech-article.json').write_text(json.dumps(article), encoding='utf-8')
    monkeypatch.setattr(step3_score, 'JSON_DIR', json_dir)
    monkeypatch.setattr(step3_score, 'SCORED_DIR', scored_dir)
    monkeypatch.setattr(step3_score, 'call_llm', lambda *args, **kwargs: '{"score": 88, "reason": "중요", "breakdown": {}}')

    result = step3_score.process_file(json_dir / 'tech-article.json')

    assert result is not None
    assert result['_source_category'] == 'tech'
    assert result['_source_query'] == 'AI'
    saved = json.loads((scored_dir / 'tech-article.json').read_text(encoding='utf-8'))
    assert saved['_source_category'] == 'tech'


def test_step4_selects_hash_article_ids_and_skips_error_files(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    _write_json(json_dir / '15e31771bf18.json')
    _write_json(json_dir / 'cc5111b6fa91.json')
    _write_json(json_dir / 'cc5111b6fa91_error.json')
    monkeypatch.setattr(step4_summarize, 'JSON_DIR', json_dir)

    assert [p.name for p in step4_summarize._input_json_files()] == [
        '15e31771bf18.json',
        'cc5111b6fa91.json',
    ]


def test_step4_selects_top_scored_articles_per_source_category(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    scored_dir = tmp_path / 'scored'
    for name in ['tech-low', 'tech-high', 'sports-only']:
        _write_json(json_dir / f'{name}.json')
    _write_json(json_dir / 'tech-error_error.json')
    scored_dir.mkdir(parents=True, exist_ok=True)
    (scored_dir / 'tech-low.json').write_text(
        json.dumps({'score': 10, '_source_category': 'tech'}), encoding='utf-8'
    )
    (scored_dir / 'tech-high.json').write_text(
        json.dumps({'score': 90, '_source_category': 'tech'}), encoding='utf-8'
    )
    (scored_dir / 'sports-only.json').write_text(
        json.dumps({'score': 50, '_source_category': 'sports'}), encoding='utf-8'
    )
    monkeypatch.setattr(step4_summarize, 'JSON_DIR', json_dir)
    monkeypatch.setattr(step4_summarize, 'SCORED_DIR', scored_dir)
    monkeypatch.setenv('PIPELINE_SELECTED_PER_CATEGORY', '1')

    assert [p.name for p in step4_summarize._input_json_files()] == [
        'sports-only.json',
        'tech-high.json',
    ]


def test_step4_writes_summary_selection_manifest(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    json_dir = data_dir / 'json'
    selected = [json_dir / 'sports-only.json', json_dir / 'tech-high.json']
    monkeypatch.setattr(step4_summarize, 'DATA_DIR', data_dir)
    monkeypatch.setenv('PIPELINE_SELECTED_PER_CATEGORY', '1')
    monkeypatch.setenv('PIPELINE_BEST_OF_N', '3')
    monkeypatch.setenv('PIPELINE_BEST_OF_SCORE_THRESHOLD', '80')

    step4_summarize._write_selection_manifest(selected, total_json_count=3)

    manifest = json.loads((data_dir / 'summary_selection.json').read_text(encoding='utf-8'))
    assert manifest['selected_article_ids'] == ['sports-only', 'tech-high']
    assert manifest['selected_count'] == 2
    assert manifest['total_json_count'] == 3
    assert manifest['selected_per_category'] == 1
    assert manifest['best_of_n'] == 3
    assert manifest['best_of_score_threshold'] == 80.0



def test_step4_best_of_n_runs_only_for_high_scored_articles_and_selects_best_candidate(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    scored_dir = tmp_path / 'scored'
    summarized_dir = tmp_path / 'summarized'
    article = {'title': '중요 기사', 'content': '중요한 경제 기사 본문입니다.'}
    json_dir.mkdir(parents=True, exist_ok=True)
    scored_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / 'important.json').write_text(json.dumps(article), encoding='utf-8')
    (scored_dir / 'important.json').write_text(json.dumps({'score': 91}), encoding='utf-8')
    monkeypatch.setattr(step4_summarize, 'JSON_DIR', json_dir)
    monkeypatch.setattr(step4_summarize, 'SCORED_DIR', scored_dir)
    monkeypatch.setattr(step4_summarize, 'SUMMARIZED_DIR', summarized_dir)
    monkeypatch.setenv('PIPELINE_BEST_OF_N', '3')
    monkeypatch.setenv('PIPELINE_BEST_OF_SCORE_THRESHOLD', '85')
    monkeypatch.setenv('PIPELINE_SKIP_INLINE_VERIFY', '1')

    responses = iter([
        {'headline_34': '가' * 31, 'headline_58': '나' * 54, 'headline_89': '다' * 82, 'summary': '첫 번째 후보'},
        {'headline_34': '가' * 33, 'headline_58': '나' * 56, 'headline_89': '다' * 86, 'summary': '두 번째 후보'},
        {'headline_34': '가' * 34, 'headline_58': '나' * 58, 'headline_89': '다' * 89, 'summary': '세 번째 후보'},
    ])
    calls = []

    def fake_call_llm(*args, **kwargs):
        calls.append(args)
        return json.dumps(next(responses), ensure_ascii=False)

    monkeypatch.setattr(step4_summarize, 'call_llm', fake_call_llm)

    result = step4_summarize.process_file(json_dir / 'important.json')

    assert result is not None
    assert len(calls) == 3
    assert result['_best_of_n'] == 3
    assert result['_best_of_candidate_index'] == 2
    saved = json.loads((summarized_dir / 'important.json').read_text(encoding='utf-8'))
    assert saved['summary'] == '세 번째 후보'
    assert len(saved['_best_of_candidates']) == 3


def test_step4_best_of_n_keeps_low_scored_articles_single_candidate(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    scored_dir = tmp_path / 'scored'
    summarized_dir = tmp_path / 'summarized'
    article = {'title': '일반 기사', 'content': '일반 기사 본문입니다.'}
    json_dir.mkdir(parents=True, exist_ok=True)
    scored_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / 'ordinary.json').write_text(json.dumps(article), encoding='utf-8')
    (scored_dir / 'ordinary.json').write_text(json.dumps({'score': 50}), encoding='utf-8')
    monkeypatch.setattr(step4_summarize, 'JSON_DIR', json_dir)
    monkeypatch.setattr(step4_summarize, 'SCORED_DIR', scored_dir)
    monkeypatch.setattr(step4_summarize, 'SUMMARIZED_DIR', summarized_dir)
    monkeypatch.setenv('PIPELINE_BEST_OF_N', '3')
    monkeypatch.setenv('PIPELINE_BEST_OF_SCORE_THRESHOLD', '85')
    monkeypatch.setenv('PIPELINE_SKIP_INLINE_VERIFY', '1')
    calls = []

    def fake_call_llm(*args, **kwargs):
        calls.append(args)
        return json.dumps({
            'headline_34': '가' * 34,
            'headline_58': '나' * 58,
            'headline_89': '다' * 89,
            'summary': '단일 후보',
        }, ensure_ascii=False)

    monkeypatch.setattr(step4_summarize, 'call_llm', fake_call_llm)

    result = step4_summarize.process_file(json_dir / 'ordinary.json')

    assert result is not None
    assert len(calls) == 1
    assert result['_best_of_n'] == 1
    assert '_best_of_candidates' not in result

def test_step5_selects_hash_summary_ids_and_skips_error_files(tmp_path, monkeypatch):
    summarized_dir = tmp_path / 'summarized'
    _write_json(summarized_dir / '5199e600904a.json')
    _write_json(summarized_dir / 'f574bfb09212.json')
    _write_json(summarized_dir / 'f574bfb09212_error.json')
    monkeypatch.setattr(step5_verify, 'SUMMARIZED_DIR', summarized_dir)

    assert [p.name for p in step5_verify._summary_files()] == [
        '5199e600904a.json',
        'f574bfb09212.json',
    ]

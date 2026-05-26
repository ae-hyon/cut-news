from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import step2_to_json


def test_process_file_attaches_crawler_category_metadata(monkeypatch, tmp_path: Path):
    json_dir = tmp_path / 'json'
    monkeypatch.setattr(step2_to_json, 'JSON_DIR', json_dir)
    raw_path = tmp_path / 'naver-1.txt'
    raw_path.write_text(
        '\n'.join(
            [
                '제목: 카테고리 기사',
                '날짜: 2026-05-26',
                '기자: 김기자',
                'URL: https://news.example.com/stock/1',
                '콘텐츠소스: body',
                '소스카테고리: stock',
                '소스쿼리: 코스피',
                '---',
                '주식시장 기사 본문입니다. 충분한 본문을 둡니다. ' * 10,
            ]
        ),
        encoding='utf-8',
    )

    monkeypatch.setattr(
        step2_to_json,
        'call_llm',
        lambda system, text, temperature, timeout: json.dumps(
            {
                'title': '카테고리 기사',
                'date': '2026-05-26',
                'author': '김기자',
                'url': 'https://news.example.com/stock/1',
                'content': '주식시장 기사 본문입니다.',
            },
            ensure_ascii=False,
        ),
    )

    status, result = step2_to_json.process_file(raw_path)

    assert status == 'success'
    assert result is not None
    assert result['content_source'] == 'body'
    assert result['source_category'] == 'stock'
    assert result['source_query'] == '코스피'
    saved = json.loads((json_dir / 'naver-1.json').read_text(encoding='utf-8'))
    assert saved['source_category'] == 'stock'

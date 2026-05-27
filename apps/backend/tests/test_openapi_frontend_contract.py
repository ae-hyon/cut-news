from __future__ import annotations

from pathlib import Path

from app.main import app
from app.common.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]


def _operation(schema: dict, path: str, method: str) -> dict:
    return schema['paths'][path][method]


def test_openapi_documents_cookie_auth_for_frontend_try_it_out():
    schema = app.openapi()

    security_schemes = schema['components']['securitySchemes']
    assert security_schemes['AccessTokenCookie'] == {
        'type': 'apiKey',
        'in': 'cookie',
        'name': settings.auth_access_cookie_name,
        'description': 'HttpOnly access-token cookie set by the Kakao callback or token refresh endpoint.',
    }

    protected_routes = [
        ('/v1/me', 'get'),
        ('/v1/me/preference', 'get'),
        ('/v1/me/preference', 'put'),
        ('/v1/me/preference', 'patch'),
        ('/v1/me/feed', 'get'),
        ('/v1/me/archive', 'get'),
        ('/v1/me/archive/{archive_date}', 'get'),
        ('/v1/me/articles/{article_id}', 'get'),
        ('/v1/me/scraps', 'get'),
        ('/v1/me/scraps/{article_id}', 'put'),
        ('/v1/me/scraps/{article_id}', 'delete'),
        ('/v1/articles/{article_id}', 'get'),
    ]
    for path, method in protected_routes:
        operation = _operation(schema, path, method)
        assert {'AccessTokenCookie': []} in operation['security']
        assert 'Authentication required' in operation['responses']['401']['description']


def test_openapi_frontend_contract_has_examples_and_actionable_descriptions():
    schema = app.openapi()

    assert 'credentials: include' in schema['info']['description']
    assert 'http://127.0.0.1:3030' in schema['info']['description']
    assert 'test-frontend' in schema['info']['description']
    assert 'deprecated' in schema['info']['description']

    get_me = _operation(schema, '/v1/me', 'get')
    assert 'session_state' in get_me['description']
    assert 'anonymous' in get_me['description']
    assert 'authenticated' in get_me['description']
    assert 'onboarded' in get_me['description']

    feed = _operation(schema, '/v1/me/feed', 'get')
    assert 'snapshot' in feed['description'].lower()
    assert 'is_scrapped' in feed['description']

    article_detail = _operation(schema, '/v1/me/articles/{article_id}', 'get')
    assert 'marks the article read' in article_detail['description']
    assert 'snapshot_id' in article_detail['description']
    assert 'snapshot_id' in [parameter['name'] for parameter in article_detail['parameters']]

    preference_schema = schema['components']['schemas']['UserPreferenceUpdateRequestSchema']
    assert preference_schema['examples'][0] == {
        'mode': 'wide',
        'primary_categories': ['macro', 'sectors', 'policy'],
        'subcategories': [],
    }

    session_schema = schema['components']['schemas']['AuthSessionResponseSchema']
    assert 'preference' in session_schema['required']
    assert session_schema['examples'][0]['session_state'] == 'anonymous'
    assert session_schema['examples'][1]['session_state'] == 'authenticated'
    assert session_schema['examples'][2]['session_state'] == 'onboarded'
    assert session_schema['examples'][2]['preference'] == {
        'mode': 'narrow',
        'primary_categories': ['macro'],
        'subcategories': ['rates-fx'],
    }

    patch_preference = _operation(schema, '/v1/me/preference', 'patch')
    assert patch_preference['summary'] == 'Update my interest categories'

    feed_schema = schema['components']['schemas']['FeedResponseSchema']
    required_feed_fields = set(feed_schema['required'])
    assert {'snapshot_id', 'feed_date', 'status', 'read_count', 'total_count'} <= required_feed_fields
    assert feed_schema['examples'][0]['snapshot_id'] == 42
    assert feed_schema['examples'][0]['blocks'][0]['articles'][0]['is_scrapped'] is False

    archive_month = _operation(schema, '/v1/me/archive', 'get')
    assert 'persisted daily feed snapshot' in archive_month['description']
    archive_date = _operation(schema, '/v1/me/archive/{archive_date}', 'get')
    assert 'marks the snapshot viewed' in archive_date['description']

    archive_day_schema = schema['components']['schemas']['ArchiveDayResponseSchema']
    assert {'snapshot_id', 'status', 'has_feed', 'read_count', 'total_count', 'first_viewed_at', 'completed_at'} <= set(archive_day_schema['required'])
    assert 'items' not in archive_day_schema.get('properties', {})

    archive_date_schema = schema['components']['schemas']['ArchiveDateResponseSchema']
    assert {'snapshot_id', 'status', 'read_count', 'total_count', 'items'} <= set(archive_date_schema['required'])


def test_openapi_documents_kakao_cookie_redirect_contract():
    schema = app.openapi()
    callback = _operation(schema, '/v1/auth/oauth/kakao/callback', 'get')

    assert 'Kakao redirects here' in callback['description']
    assert 'Set-Cookie' in callback['description']
    assert 'annoyingcap_access_token' in callback['description']
    assert 'annoyingcap_refresh_token' in callback['description']
    assert callback['responses']['302']['description'].startswith('Redirects to the real Next frontend')
    assert 'http://127.0.0.1:3030/onboarding/complete' in callback['responses']['302']['description']
    assert callback['responses']['401']['description'] == 'Invalid or expired OAuth state.'


def test_backend_docs_and_compose_use_current_frontend_contract():
    readme = (REPO_ROOT / 'apps/backend/README.md').read_text(encoding='utf-8')
    env_example = (REPO_ROOT / 'apps/backend/.env.example').read_text(encoding='utf-8')
    compose = (REPO_ROOT / 'apps/backend/docker-compose.yml').read_text(encoding='utf-8')

    assert 'FRONTEND_APP_URL=http://127.0.0.1:3030' in readme
    assert 'FRONTEND_APP_URL=http://127.0.0.1:3030' in env_example
    assert 'FRONTEND_APP_URL: http://127.0.0.1:3030' in compose
    assert 'KAKAO_REDIRECT_URI: http://127.0.0.1:8030/v1/auth/oauth/kakao/callback' in compose
    assert 'http://127.0.0.1:5173' not in readme
    assert 'http://127.0.0.1:5173' not in env_example

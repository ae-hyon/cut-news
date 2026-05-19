from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def preflight(origin: str):
    return TestClient(app).options(
        '/v1/me',
        headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'content-type',
        },
    )


def test_cors_allows_localhost_and_loopback_frontend_origins():
    for origin in ('http://127.0.0.1:3000', 'http://localhost:3000'):
        response = preflight(origin)

        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == origin
        assert response.headers['access-control-allow-credentials'] == 'true'

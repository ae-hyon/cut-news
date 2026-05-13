from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.api.router import api_router


def test_legacy_user_and_auth_routes_are_not_registered():
    app = FastAPI()
    app.include_router(api_router)
    client = TestClient(app)

    assert client.get('/v1/auth/session').status_code == 405
    assert client.get('/v1/auth/kakao/start').status_code == 404
    assert client.post('/v1/auth/refresh').status_code == 404
    assert client.post('/v1/auth/logout').status_code == 404
    assert client.get('/v1/users/demo-user/preferences').status_code == 404
    assert client.get('/v1/users/demo-user/feed').status_code == 404
    assert client.get('/v1/users/demo-user/scraps').status_code == 404
    assert client.post('/v1/summaries', json={}).status_code == 404

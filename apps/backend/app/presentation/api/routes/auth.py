from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import JSONResponse, RedirectResponse

from app.application.services.auth_service import AuthError, AuthService
from app.common.config import settings
from app.domain.entities import AuthSession
from app.presentation.api.dependencies import get_auth_service, get_current_session
from app.presentation.schemas import AuthLogoutResponseSchema, AuthSessionResponseSchema, AuthStartResponseSchema

router = APIRouter(tags=['auth'])


def _kakao_callback_completion_response(result: dict) -> RedirectResponse:
    frontend_url = f"{settings.frontend_app_url.rstrip('/')}/?auth=kakao"
    response = RedirectResponse(url=frontend_url, status_code=302)
    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=result['access_token'],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path='/',
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=result['refresh_token'],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path='/',
    )
    return response


@router.post('/auth/oauth/kakao/authorization', response_model=AuthStartResponseSchema)
def create_kakao_authorization(service: AuthService = Depends(get_auth_service)):
    return AuthStartResponseSchema.model_validate(service.start_kakao_auth())


@router.get('/auth/oauth/kakao/callback')
def kakao_callback(code: str, state: str, service: AuthService = Depends(get_auth_service)):
    try:
        result = service.complete_kakao_callback(code=code, state=state)
    except AuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={'code': exc.code, 'message': exc.message},
        )
    if hasattr(result, 'model_dump'):
        result = result.model_dump()

    return _kakao_callback_completion_response(result)


@router.get('/me', response_model=AuthSessionResponseSchema, tags=['me'])
def get_me(session: AuthSession = Depends(get_current_session)):
    payload = session.model_dump() if hasattr(session, 'model_dump') else session
    return AuthSessionResponseSchema.model_validate(payload)


@router.post('/auth/token/refresh', response_model=AuthSessionResponseSchema)
def refresh_auth_session(
    annoyingcap_refresh_token: str | None = Cookie(default=None),
    service: AuthService = Depends(get_auth_service),
):
    try:
        result = service.refresh_session(annoyingcap_refresh_token or '')
    except AuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={'code': exc.code, 'message': exc.message},
        )
    payload = result.model_dump() if hasattr(result, 'model_dump') else result
    response = JSONResponse(content=AuthSessionResponseSchema.model_validate(payload['session']).model_dump())
    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=payload['access_token'],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path='/',
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=payload['refresh_token'],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path='/',
    )
    return response


@router.delete('/auth/session', response_model=AuthLogoutResponseSchema)
def delete_auth_session(
    annoyingcap_refresh_token: str | None = Cookie(default=None),
    service: AuthService = Depends(get_auth_service),
):
    service.logout(annoyingcap_refresh_token)
    response = JSONResponse(content=AuthLogoutResponseSchema(ok=True).model_dump())
    response.delete_cookie(settings.auth_access_cookie_name, path='/')
    response.delete_cookie(settings.auth_refresh_cookie_name, path='/')
    return response

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import JSONResponse, RedirectResponse

from app.application.services.auth_service import AuthError, AuthService
from app.common.config import settings
from app.presentation.api.dependencies import get_auth_service
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


@router.get('/auth/kakao/start', response_model=AuthStartResponseSchema)
def start_kakao_auth(service: AuthService = Depends(get_auth_service)):
    return AuthStartResponseSchema.model_validate(service.start_kakao_auth())


@router.get('/auth/kakao/callback')
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


@router.get('/auth/session', response_model=AuthSessionResponseSchema)
def get_auth_session(
    user_id: str | None = None,
    provider: str | None = None,
    provider_subject: str | None = None,
    annoyingcap_access_token: str | None = Cookie(default=None),
    service: AuthService = Depends(get_auth_service),
):
    result = service.resolve_session(
        user_id=user_id,
        provider=provider,
        provider_subject=provider_subject,
        access_token=None if user_id or (provider and provider_subject) else annoyingcap_access_token,
    )
    if hasattr(result, 'model_dump'):
        result = result.model_dump()
    return AuthSessionResponseSchema.model_validate(result)


@router.post('/auth/refresh', response_model=AuthSessionResponseSchema)
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


@router.post('/auth/logout', response_model=AuthLogoutResponseSchema)
def logout(
    annoyingcap_refresh_token: str | None = Cookie(default=None),
    service: AuthService = Depends(get_auth_service),
):
    service.logout(annoyingcap_refresh_token)
    response = JSONResponse(content=AuthLogoutResponseSchema(ok=True).model_dump())
    response.delete_cookie(settings.auth_access_cookie_name, path='/')
    response.delete_cookie(settings.auth_refresh_cookie_name, path='/')
    return response

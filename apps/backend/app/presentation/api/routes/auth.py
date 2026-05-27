from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.application.services.auth_service import AuthError, AuthService
from app.common.config import settings
from app.domain.entities import AuthSession
from app.presentation.api.dependencies import get_auth_service, get_current_session
from app.presentation.schemas import AuthLogoutResponseSchema, AuthSessionResponseSchema, AuthStartResponseSchema

router = APIRouter(tags=['auth'])


def _request_callback_uri(request: Request) -> str:
    """Return the externally visible Kakao callback URI for this request.

    Local ports are intentionally derived from the incoming backend request so
    changing 8000 -> 8030 does not require editing KAKAO_REDIRECT_URI. Explicit
    proxy headers still work for deployed environments behind a gateway.
    """
    forwarded_proto = request.headers.get('x-forwarded-proto')
    forwarded_host = request.headers.get('x-forwarded-host') or request.headers.get('host')
    path = request.url_for('kakao_callback').components.path
    if forwarded_proto and forwarded_host:
        return f'{forwarded_proto}://{forwarded_host}{path}'
    return str(request.url_for('kakao_callback'))


def _callback_uri_from_current_request(request: Request) -> str:
    return str(request.url.remove_query_params(['code', 'state']))


def _frontend_origin_from_request(request: Request) -> str:
    origin = request.headers.get('origin')
    allowed_origins = set(settings.resolved_cors_allowed_origins)
    if origin and origin.rstrip('/') in allowed_origins:
        return origin.rstrip('/')
    referer = request.headers.get('referer')
    if referer:
        parsed = urlparse(referer)
        referer_origin = f'{parsed.scheme}://{parsed.netloc}'
        if referer_origin in allowed_origins:
            return referer_origin
    return settings.frontend_app_url.rstrip('/')


def _kakao_callback_completion_response(result: dict) -> RedirectResponse:
    frontend_origin = result.get('oauth_frontend_url') or settings.frontend_app_url
    frontend_url = f"{frontend_origin.rstrip('/')}/onboarding/complete?auth=kakao"
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


@router.post(
    '/auth/oauth/kakao/authorization',
    response_model=AuthStartResponseSchema,
    summary='Start Kakao OAuth login',
    description=(
        'Creates a short-lived OAuth state and returns the Kakao authorization_url. '
        'Open this URL in a popup or redirect. The final Kakao callback sets HttpOnly cookies.'
    ),
)
def create_kakao_authorization(request: Request, service: AuthService = Depends(get_auth_service)):
    return AuthStartResponseSchema.model_validate(
        service.start_kakao_auth(
            redirect_uri=_request_callback_uri(request),
            frontend_origin=_frontend_origin_from_request(request),
        )
    )


@router.get(
    '/auth/oauth/kakao/callback',
    summary='Complete Kakao OAuth login',
    description=(
        'Kakao redirects here with code and state. On success the backend sets Set-Cookie headers for '
        'annoyingcap_access_token and annoyingcap_refresh_token, then redirects to the real Next frontend. '
        'Frontend should then call GET /v1/me with credentials: include to resolve session_state.'
    ),
    responses={
        302: {
            'description': (
                'Redirects to the real Next frontend at '
                'http://127.0.0.1:3030/onboarding/complete with the Kakao auth query after setting auth cookies.'
            )
        },
        401: {'description': 'Invalid or expired OAuth state.'},
    },
)
def kakao_callback(code: str, state: str, request: Request, service: AuthService = Depends(get_auth_service)):
    try:
        result = service.complete_kakao_callback(code=code, state=state, redirect_uri=_callback_uri_from_current_request(request))
    except AuthError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={'code': exc.code, 'message': exc.message},
        )
    if hasattr(result, 'model_dump'):
        result = result.model_dump()

    return _kakao_callback_completion_response(result)


@router.get(
    '/me',
    response_model=AuthSessionResponseSchema,
    tags=['me'],
    summary='Resolve current frontend session',
    description=(
        'Returns the current cookie-auth session. Frontend routing should be based on session_state: '
        'anonymous means no valid login cookie, authenticated means logged in but onboarding is incomplete, '
        'and onboarded means logged in with completed preferences.'
    ),
    responses={401: {'description': 'Authentication required'}},
)
def get_me(session: AuthSession = Depends(get_current_session)):
    payload = session.model_dump() if hasattr(session, 'model_dump') else session
    return AuthSessionResponseSchema.model_validate(payload)


@router.post(
    '/auth/token/refresh',
    response_model=AuthSessionResponseSchema,
    summary='Refresh auth cookies',
    description='Uses the HttpOnly refresh cookie to rotate auth cookies and returns the updated session payload.',
    responses={401: {'description': 'Refresh token is missing, invalid, expired, or revoked.'}},
)
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


@router.delete(
    '/auth/session',
    response_model=AuthLogoutResponseSchema,
    summary='Logout current session',
    description='Revokes the refresh session when present and deletes both auth cookies.',
)
def delete_auth_session(
    annoyingcap_refresh_token: str | None = Cookie(default=None),
    service: AuthService = Depends(get_auth_service),
):
    service.logout(annoyingcap_refresh_token)
    response = JSONResponse(content=AuthLogoutResponseSchema(ok=True).model_dump())
    response.delete_cookie(settings.auth_access_cookie_name, path='/')
    response.delete_cookie(settings.auth_refresh_cookie_name, path='/')
    return response

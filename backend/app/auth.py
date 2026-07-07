"""
Shared-password access control for hosting the app online.

Design: one group password -> HMAC-signed expiry cookie. No accounts and no
session storage - if you know the squad password you're in, and a session
lasts settings.auth_session_days. auth_enabled defaults to False so local
development behaves exactly as it always has.

The middleware gates every route (including /docs and /openapi.json) except
PUBLIC_PATHS and CORS preflights. Destructive admin endpoints additionally
take the require_admin dependency, enforced only when ADMIN_TOKEN is set.
"""
import hashlib
import hmac
import logging
import secrets
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings

logger = logging.getLogger(__name__)

COOKIE_NAME = "sc2mmr_session"

# Reachable without a session. Everything else needs auth when enabled.
PUBLIC_PATHS = {"/health", "/auth/login", "/auth/logout", "/auth/status"}

# In public-read mode these stay session-gated even though they are GETs:
# replay downloads are the one path where a stored file reaches a visitor's
# machine (malware-distribution defense), and the interactive API docs are
# developer surface, not ladder data.
_PROTECTED_READ_EXACT = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}


def _is_protected_read(path: str) -> bool:
    if path in _PROTECTED_READ_EXACT:
        return True
    # GET /replays/matches/{id}/download
    return path.startswith("/replays/") and path.rstrip("/").endswith("/download")


# =============================================================================
# Session tokens: "<expiry-unix-ts>.<hmac-sha256>"
# =============================================================================

_runtime_secret: Optional[str] = None


def _secret() -> bytes:
    """Signing secret: AUTH_SECRET if configured, else a per-process random.

    The per-process fallback is secure (unforgeable) but means every restart
    invalidates all sessions - fine for trying things out, annoying in
    production, hence the startup warning.
    """
    global _runtime_secret
    if settings.auth_secret:
        return settings.auth_secret.encode()
    if _runtime_secret is None:
        _runtime_secret = secrets.token_hex(32)
        logger.warning(
            "AUTH_SECRET is not set - using a generated per-process secret; "
            "all sessions will reset whenever the server restarts"
        )
    return _runtime_secret.encode()


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token() -> str:
    expires = int(time.time()) + settings.auth_session_days * 86400
    payload = str(expires)
    return f"{payload}.{_sign(payload)}"


def verify_session_token(token: str) -> bool:
    try:
        payload, signature = token.rsplit(".", 1)
    except (ValueError, AttributeError):
        return False
    if not hmac.compare_digest(signature, _sign(payload)):
        return False
    try:
        return int(payload) > time.time()
    except ValueError:
        return False


# =============================================================================
# Login rate limiting (in-memory; the deployment runs a single instance)
# =============================================================================

_failed_attempts: Dict[str, List[float]] = {}
_ATTEMPT_WINDOW_SECONDS = 900.0
_MAX_ATTEMPTS_PER_WINDOW = 20


def _too_many_attempts(ip: str) -> bool:
    now = time.time()
    recent = [t for t in _failed_attempts.get(ip, []) if now - t < _ATTEMPT_WINDOW_SECONDS]
    _failed_attempts[ip] = recent
    return len(recent) >= _MAX_ATTEMPTS_PER_WINDOW


def _record_failure(ip: str) -> None:
    _failed_attempts.setdefault(ip, []).append(time.time())


def _clear_failures(ip: str) -> None:
    _failed_attempts.pop(ip, None)


# =============================================================================
# Middleware
# =============================================================================

class RequireSessionMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests with 401 when auth is enabled.

    Must sit INSIDE CORSMiddleware (i.e. be added to the app before it) so
    preflight OPTIONS requests short-circuit in CORS land and 401 responses
    still carry CORS headers for the browser to read.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        # Public-read mode: anonymous GET/HEAD is fine for ladder data; every
        # write and every protected read still needs the session.
        if (
            settings.auth_public_read
            and request.method in ("GET", "HEAD")
            and not _is_protected_read(request.url.path)
        ):
            return await call_next(request)
        token = request.cookies.get(COOKIE_NAME, "")
        if token and verify_session_token(token):
            return await call_next(request)
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})


# =============================================================================
# Admin gate dependency
# =============================================================================

def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Gate for destructive/admin endpoints.

    Only enforced when ADMIN_TOKEN is configured, so local development and
    the existing scripts keep working unchanged until the operator opts in.
    """
    if not settings.admin_token:
        return
    if not x_admin_token or not hmac.compare_digest(
        x_admin_token.encode(), settings.admin_token.encode()
    ):
        raise HTTPException(status_code=403, detail="Admin token required")


# =============================================================================
# Routes
# =============================================================================

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


def _set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    if not settings.auth_enabled:
        return {"auth_enabled": False, "authenticated": True}
    if not settings.group_password:
        raise HTTPException(
            status_code=503,
            detail="Server is missing GROUP_PASSWORD configuration",
        )
    ip = request.client.host if request.client else "unknown"
    if _too_many_attempts(ip):
        raise HTTPException(status_code=429, detail="Too many attempts - try again later")
    if not hmac.compare_digest(
        body.password.encode(), settings.group_password.encode()
    ):
        _record_failure(ip)
        raise HTTPException(status_code=401, detail="Wrong password")
    _clear_failures(ip)
    _set_session_cookie(
        response, create_session_token(), settings.auth_session_days * 86400
    )
    return {"auth_enabled": True, "authenticated": True}


@router.post("/logout")
def logout(response: Response):
    # Expire the cookie with the same attributes it was set with, or
    # cross-site browsers won't apply the deletion.
    _set_session_cookie(response, "", 0)
    return {"auth_enabled": settings.auth_enabled, "authenticated": False}


@router.get("/status")
def auth_status(request: Request):
    """Lets the frontend decide whether to show the login screen."""
    if not settings.auth_enabled:
        return {"auth_enabled": False, "public_read": True, "authenticated": True}
    token = request.cookies.get(COOKIE_NAME, "")
    return {
        "auth_enabled": True,
        "public_read": settings.auth_public_read,
        "authenticated": bool(token and verify_session_token(token)),
    }

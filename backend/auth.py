"""Enterprise identity and role helpers.

Local mode keeps the workshop-friendly identity headers. JWT/OIDC modes validate
Bearer tokens, including signature, issuer/audience, and JWKS key rotation.

Security hardening (WEB-005, WEB-023, AGT-010):
- Production mode requires JWT/OIDC auth
- HS256 algorithm removed (only RS256, ES256 allowed)
- Local auth mode logs warnings and is blocked in production
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from typing import Literal

import httpx
import jwt
from fastapi import HTTPException, Request, status
from pydantic import BaseModel

from .audit import set_actor_context
from .settings import AppSettings, get_settings

logger = logging.getLogger("backend.auth")

Role = Literal["learner", "educator", "admin"]
ALLOWED_ROLES = {"learner", "educator", "admin"}

# WEB-023: Only allow asymmetric algorithms (no HS256)
SECURE_JWT_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256", "PS384", "PS512"}
# Algorithms that should be rejected
INSECURE_ALGORITHMS = {"HS256", "HS384", "HS512", "none"}


class Identity(BaseModel):
    user_id: str
    tenant_id: str
    role: Role
    claims: dict[str, Any] = {}


@dataclass
class _JWKSCache:
    keys: list[dict[str, Any]]
    expires_at: float


_jwks_cache: _JWKSCache | None = None
_discovery_cache: tuple[str, float] | None = None


def validate_auth_config(settings: AppSettings) -> None:
    """Validate auth configuration at startup (WEB-005, AGT-010).

    Raises RuntimeError if configuration is insecure for production.
    """
    if settings.is_production:
        if settings.auth_mode in {"local", "disabled"}:
            raise RuntimeError(
                f"SECURITY ERROR: auth_mode='{settings.auth_mode}' is not allowed in production. "
                "Set TUTOR_AUTH_MODE to 'jwt' or 'oidc' with proper configuration. (WEB-005)"
            )
        # Ensure JWT algorithms are secure
        for alg in settings.auth_jwt_algorithms:
            if alg.upper() in INSECURE_ALGORITHMS:
                raise RuntimeError(
                    f"SECURITY ERROR: Insecure JWT algorithm '{alg}' configured in production. "
                    f"Use only: {', '.join(sorted(SECURE_JWT_ALGORITHMS))}. (WEB-023)"
                )
    elif settings.auth_mode == "local":
        logger.warning(
            "Running with auth_mode='local' - authentication relies on client-provided headers. "
            "This is acceptable for development but MUST NOT be used in production. (WEB-005)"
        )
    elif settings.auth_mode == "disabled":
        logger.warning(
            "Running with auth_mode='disabled' - all requests use default identity. "
            "This is acceptable for development but MUST NOT be used in production. (WEB-005)"
        )


def _auth_error(message: str = "Invalid authentication token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _config_error(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization") or request.headers.get("Authorization")
    if not authorization:
        raise _auth_error("Missing bearer token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _auth_error("Authorization header must use Bearer token")
    return token.strip()


def _claim(claims: dict[str, Any], path: str) -> Any:
    value: Any = claims
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _role_from_claim(value: Any) -> Role:
    if isinstance(value, str):
        role = value.lower()
        if role in ALLOWED_ROLES:
            return role  # type: ignore[return-value]
    if isinstance(value, list):
        normalized = {str(item).lower() for item in value}
        for role in ("admin", "educator", "learner"):
            if role in normalized:
                return role  # type: ignore[return-value]
    raise _auth_error("Token does not contain an allowed tutor role")


def _jwks_url(settings: AppSettings) -> str:
    global _discovery_cache
    if settings.oidc_jwks_url:
        return settings.oidc_jwks_url
    now = time.time()
    if _discovery_cache and _discovery_cache[1] > now:
        return _discovery_cache[0]
    discovery_url = settings.oidc_discovery_url
    if not discovery_url and settings.auth_issuer:
        discovery_url = settings.auth_issuer.rstrip("/") + "/.well-known/openid-configuration"
    if not discovery_url:
        raise _config_error("TUTOR_OIDC_JWKS_URL or TUTOR_OIDC_DISCOVERY_URL is required for OIDC auth")
    try:
        response = httpx.get(discovery_url, timeout=10)
        response.raise_for_status()
        jwks_uri = response.json().get("jwks_uri")
    except Exception as exc:  # pragma: no cover - exact network error varies
        raise _auth_error("Unable to fetch OIDC discovery metadata") from exc
    if not jwks_uri:
        raise _auth_error("OIDC discovery metadata did not include jwks_uri")
    _discovery_cache = (jwks_uri, now + settings.oidc_jwks_cache_ttl_seconds)
    return jwks_uri


def _fetch_jwks(settings: AppSettings, *, refresh: bool = False) -> list[dict[str, Any]]:
    global _jwks_cache
    now = time.time()
    if not refresh and _jwks_cache and _jwks_cache.expires_at > now:
        return _jwks_cache.keys
    try:
        response = httpx.get(_jwks_url(settings), timeout=10)
        response.raise_for_status()
        keys = response.json().get("keys") or []
    except Exception as exc:  # pragma: no cover - exact network error varies
        raise _auth_error("Unable to fetch OIDC signing keys") from exc
    if not isinstance(keys, list) or not keys:
        raise _auth_error("OIDC JWKS did not include signing keys")
    _jwks_cache = _JWKSCache(keys=keys, expires_at=now + settings.oidc_jwks_cache_ttl_seconds)
    return keys


def _jwk_for_token(token: str, settings: AppSettings) -> Any:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise _auth_error() from exc
    algorithm = header.get("alg")
    if algorithm not in settings.auth_jwt_algorithms:
        raise _auth_error("Token signing algorithm is not allowed")
    kid = header.get("kid")
    for refresh in (False, True):
        for key_data in _fetch_jwks(settings, refresh=refresh):
            if kid is None or key_data.get("kid") == kid:
                return jwt.PyJWK.from_dict(key_data, algorithm=algorithm).key
    raise _auth_error("No matching OIDC signing key found")


def _decode_token(token: str, settings: AppSettings) -> dict[str, Any]:
    if settings.auth_mode == "oidc":
        key = _jwk_for_token(token, settings)
    else:
        key = settings.auth_jwt_secret or settings.auth_jwt_public_key
        if not key:
            raise _config_error("TUTOR_AUTH_JWT_SECRET or TUTOR_AUTH_JWT_PUBLIC_KEY is required for JWT auth")
    options = {
        "require": ["exp", "iat"],
        "verify_aud": settings.auth_audience is not None,
        "verify_iss": settings.auth_issuer is not None,
    }
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=settings.auth_jwt_algorithms,
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
            options=options,
        )
    except jwt.ExpiredSignatureError as exc:
        raise _auth_error("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise _auth_error() from exc
    if not isinstance(claims, dict):
        raise _auth_error()
    return claims


def _identity_from_token(request: Request, settings: AppSettings) -> Identity:
    claims = _decode_token(_extract_bearer_token(request), settings)
    user_id = _claim(claims, settings.auth_user_claim)
    tenant_id = _claim(claims, settings.auth_tenant_claim)
    if not user_id:
        raise _auth_error("Token does not contain a tutor user id")
    if not tenant_id:
        if settings.auth_require_tenant_claim:
            raise _auth_error("Token does not contain a tutor tenant id")
        tenant_id = settings.local_tenant_id
    role = _role_from_claim(_claim(claims, settings.auth_role_claim))
    return Identity(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role=role,
        claims={
            "issuer": claims.get("iss"),
            "subject": claims.get("sub"),
            "audience": claims.get("aud"),
        },
    )


def get_identity(request: Request) -> Identity:
    settings = get_settings()
    if settings.auth_mode == "disabled":
        identity = Identity(
            user_id=settings.local_user_id,
            tenant_id=settings.local_tenant_id,
            role="admin",
        )
    elif settings.auth_mode in {"jwt", "oidc"}:
        identity = _identity_from_token(request, settings)
    else:
        role = request.headers.get("x-tutor-role", settings.local_role).lower()
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tutor role")
        identity = Identity(
            user_id=request.headers.get("x-tutor-user-id", settings.local_user_id),
            tenant_id=request.headers.get("x-tutor-tenant-id", settings.local_tenant_id),
            role=role,  # type: ignore[arg-type]
        )
    set_actor_context(identity.tenant_id, identity.user_id, identity.role)
    return identity


def require_role(identity: Identity, allowed: set[Role]) -> None:
    if identity.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not allowed for this action")


def require_learner_access(identity: Identity, learner_id: str) -> None:
    if identity.role == "learner" and identity.user_id != learner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Learners can only access their own state")

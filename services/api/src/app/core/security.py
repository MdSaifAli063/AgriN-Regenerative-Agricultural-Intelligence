import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.deps import get_db
from app.core.exceptions import ForbiddenException
from app.models.farm import Farm, Field
from app.models.user import User
import bcrypt

security_bearer = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Computes bcrypt hash of a password."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")



# In-memory JWKS cache: {keys: List[Dict], expires_at: float}
_jwks_cache: Dict[str, Any] = {"keys": [], "expires_at": 0.0}


def create_dev_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token used for dev mode or internal routing."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iss": "krishinet-dev-auth"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_keycloak_jwks() -> List[Dict[str, Any]]:
    """Fetches and caches Keycloak JWKS keys for 1 hour."""
    now = time.time()
    if _jwks_cache["keys"] and now < _jwks_cache["expires_at"]:
        return _jwks_cache["keys"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(settings.KEYCLOAK_JWKS_URL)
            if resp.status_code == 200:
                keys = resp.json().get("keys", [])
                _jwks_cache["keys"] = keys
                _jwks_cache["expires_at"] = now + 3600.0
                return keys
    except Exception:
        pass
    return []


async def decode_token_payload(token: str) -> Dict[str, Any]:
    """Decodes token either via Keycloak JWKS or Dev Secret depending on environment."""
    # 1. First try Dev Secret / Dev Bypass
    if settings.DEV_AUTH_BYPASS and settings.ENVIRONMENT in ["dev", "development", "test", "testing"]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            pass

    # 2. Try Keycloak JWKS verification
    jwks = await get_keycloak_jwks()
    if jwks:
        try:
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks:
                if key["kid"] == unverified_header.get("kid"):
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"],
                    }
                    break
            if rsa_key:
                return jwt.decode(
                    token,
                    rsa_key,
                    algorithms=["RS256"],
                    audience=settings.KEYCLOAK_CLIENT_ID,
                    issuer=f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}",
                )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Keycloak token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Fallback standard symmetric decode
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency resolving authenticated User model."""
    if not auth_header:
        if settings.DEV_AUTH_BYPASS and settings.ENVIRONMENT in ["dev", "development"]:
            # Ephemeral demo farmer user
            return User(
                id="demo-farmer-id-india-001",
                country_iso="IND",
                phone_number="+919876543210",
                full_name="Ramesh Patil (Dev Farmer)",
                role="farmer",
                preferred_language="hi",
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = await decode_token_payload(auth_header.credentials)
    user_id = payload.get("sub") or payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject identifier.",
        )

    # Query user from DB
    from app.repositories.user_repo import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        user = await repo.get_by_keycloak_sub(user_id)

    if not user:
        if settings.DEV_AUTH_BYPASS:
            # Construct ephemeral user from token claims
            return User(
                id=user_id,
                country_iso=payload.get("country", settings.NODE_COUNTRY),
                phone_number=payload.get("phone", "+919876543210"),
                full_name=payload.get("name", "Demo User"),
                role=payload.get("role", "farmer"),
                preferred_language=payload.get("lang", "en"),
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User record not found in system.")

    return user


def require_roles(*allowed_roles: str):
    """Enforces role-based access control (RBAC)."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(
                f"Role '{current_user.role}' lacks permission. Required one of: {list(allowed_roles)}"
            )
        return current_user

    return role_checker


def check_farm_ownership(user: User, farm: Farm, require_write: bool = False) -> None:
    """
    Enforces data ownership:
    - Farmer: must be direct owner
    - Extension Officer: read-only access within national jurisdiction
    - Researcher: read-only access for cross-border analytics (cannot mutate farms)
    - Government Admin: node-wide administrative access
    """
    if require_write and user.role not in ["farmer", "government_admin"]:
        raise ForbiddenException(f"Role '{user.role}' cannot modify farm records.")
    if user.role == "farmer" and farm.user_id != user.id:
        raise ForbiddenException("Access denied: You do not have permission to view or modify this farm.")
    if user.role == "extension_officer" and farm.country_iso != user.country_iso:
        raise ForbiddenException("Access denied: Farm is outside your regional jurisdiction.")
    if user.role == "researcher" and require_write:
        raise ForbiddenException("Researchers have read-only access to farm records.")


async def get_current_user_optional(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Optional authentication dependency; returns None if unauthenticated."""
    if not auth_header or not auth_header.credentials:
        return None
    try:
        return await get_current_user(auth_header=auth_header, db=db)
    except HTTPException:
        return None



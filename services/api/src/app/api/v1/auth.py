from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.core.config import settings
from app.core.exceptions import ForbiddenException
from app.core.security import create_dev_token, get_current_user
from app.models.user import User
from app.schemas.auth import DevLoginRequest, RoleListResponse, TokenResponse, UserProfileResponse

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile and roles of authenticated user."""
    return current_user


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(req: DevLoginRequest, request: Request):
    """
    Developer / Demo login endpoint.
    ONLY available when DEV_AUTH_BYPASS=true and not in production.
    """
    if settings.ENVIRONMENT in ["prod", "production"] or not settings.DEV_AUTH_BYPASS:
        raise ForbiddenException("Dev login is disabled in this environment.")

    token_data = {
        "sub": req.user_id or "demo-user-001",
        "user_id": req.user_id or "demo-user-001",
        "role": req.role,
        "country": req.country_iso,
        "name": req.full_name,
        "phone": req.phone_number,
    }

    token = create_dev_token(token_data, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=req.role,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/roles", response_model=RoleListResponse)
async def list_available_roles():
    """List valid system roles in KrishiNet-BRICS."""
    return RoleListResponse(
        roles=["farmer", "extension_officer", "government_admin", "researcher"]
    )

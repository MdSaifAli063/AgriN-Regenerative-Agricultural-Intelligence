from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DevLoginRequest(BaseModel):
    user_id: Optional[str] = Field("demo-farmer-id-india-001", examples=["demo-farmer-id-india-001"])
    role: str = Field("farmer", examples=["farmer", "extension_officer", "government_admin", "researcher"])
    country_iso: str = Field("IND", examples=["IND", "BRA", "ZAF"])
    full_name: str = Field("Ramesh Patil", examples=["Ramesh Patil"])
    phone_number: str = Field("+919876543210", examples=["+919876543210"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_minutes: int


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    country_iso: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    full_name: str
    preferred_language: str
    role: str
    is_verified: bool
    created_at: Optional[datetime] = None


class RoleListResponse(BaseModel):
    roles: List[str]

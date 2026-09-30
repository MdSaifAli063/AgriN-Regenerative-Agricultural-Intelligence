from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BricsCountrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., max_length=3, examples=["IND"])
    name: str = Field(..., examples=["India"])
    national_registry_url: str
    contact_agency: str
    is_active: bool = True


class UserBase(BaseModel):
    country_code: str = Field(..., max_length=3, examples=["IND"])
    phone_number: Optional[str] = Field(None, examples=["+919876543210"])
    email: Optional[EmailStr] = None
    full_name: str = Field(..., examples=["Ramesh Patil"])
    preferred_language: str = Field("hi", examples=["hi"])
    role: str = Field("farmer", examples=["farmer"])


class UserCreate(UserBase):
    password: Optional[str] = Field(None, min_length=6)


class UserLogin(BaseModel):
    phone_or_email: str = Field(..., examples=["+919876543210"])
    password: Optional[str] = Field(None, examples=["demo123"])
    otp: Optional[str] = Field(None, examples=["123456"])


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ConsentUpdate(BaseModel):
    share_anonymized_soil: bool = True
    share_disease_telemetry: bool = True
    participate_in_federated_learning: bool = True

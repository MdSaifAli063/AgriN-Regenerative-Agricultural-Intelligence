from typing import Literal
from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"] = Field(
        ..., description="Supported MIME types for crop leaf imagery"
    )
    file_size_bytes: int = Field(
        ..., gt=0, le=10 * 1024 * 1024, description="Max upload size 10MB"
    )


class PresignUploadResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in_seconds: int = 900
    fields: dict = {}

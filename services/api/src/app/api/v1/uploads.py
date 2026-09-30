from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.upload import PresignUploadRequest, PresignUploadResponse
from app.services.storage import storage_service

router = APIRouter(prefix="/uploads", tags=["Object Storage & Leaf Imagery"])


@router.post("/presign", response_model=PresignUploadResponse, status_code=status.HTTP_201_CREATED)
async def generate_presigned_upload_url(
    req: PresignUploadRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generates a secure presigned upload URL for leaf disease diagnostics.
    Enforces random UUID object keys, supported MIME types, and 10MB size ceiling.
    """
    url, object_key, fields = storage_service.generate_presigned_upload(
        content_type=req.content_type, expires_in_seconds=900
    )
    return PresignUploadResponse(
        upload_url=url,
        object_key=object_key,
        expires_in_seconds=900,
        fields=fields,
    )

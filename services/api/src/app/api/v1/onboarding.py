import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.deps import get_db
from app.core.security import create_dev_token
from app.models.farm import CropHistory, Farm, Field
from app.models.user import Consent, User
from app.repositories.audit_repo import AuditRepository
from app.schemas.farm import OnboardingRequest, OnboardingResponse
from app.services.geo_service import GeoService

router = APIRouter(prefix="/onboarding", tags=["Farmer 60-Second Onboarding"])


@router.post("", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
async def complete_onboarding(
    req: OnboardingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes the entire 60-second farmer onboarding inside a single atomic transaction:
    - Creates or retrieves User
    - Persists Consent choices
    - Creates Farm
    - Validates & persists Field polygon via Shapely
    - Seeds initial CropHistory
    - Returns JWT token for instant dashboard access
    """
    # 1. Validate field geometry upfront
    centroid_lat, centroid_lon, area_ha = GeoService.validate_and_compute_metrics(
        req.boundary_geojson
    )

    # 2. Check if user with phone already exists
    user_query = await db.execute(select(User).where(User.phone_number == req.phone_number))
    user = user_query.scalar_one_or_none()

    if not user:
        user = User(
            id=str(uuid.uuid4()),
            country_iso=req.country_iso,
            phone_number=req.phone_number,
            full_name=req.full_name,
            preferred_language=req.preferred_language,
            role="farmer",
            is_verified=True,
        )
        db.add(user)
        await db.flush()

    # 3. Create or update Consent
    consent_query = await db.execute(select(Consent).where(Consent.user_id == user.id))
    consent = consent_query.scalar_one_or_none()
    if not consent:
        consent = Consent(
            id=str(uuid.uuid4()),
            user_id=user.id,
            share_anonymized_soil=req.share_anonymized_soil,
            share_outbreak_telemetry=req.share_outbreak_telemetry,
            participate_in_federated_learning=req.participate_in_federated_learning,
        )
        db.add(consent)
    else:
        consent.share_anonymized_soil = req.share_anonymized_soil
        consent.share_outbreak_telemetry = req.share_outbreak_telemetry
        consent.participate_in_federated_learning = req.participate_in_federated_learning

    # 4. Create Farm
    farm = Farm(
        id=str(uuid.uuid4()),
        user_id=user.id,
        farm_name=req.farm_name,
        village_district=req.village_district,
        state_province=req.state_province,
        country_iso=req.country_iso,
        total_area_hectares=area_ha,
    )
    db.add(farm)
    await db.flush()

    # 5. Create Field
    field = Field(
        id=str(uuid.uuid4()),
        farm_id=farm.id,
        field_name=req.field_name,
        boundary_geojson=req.boundary_geojson,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
        area_hectares=area_ha,
        irrigation_type=req.irrigation_type,
        current_crop=req.current_crop,
    )
    db.add(field)
    await db.flush()

    # 6. Initial Crop History
    crop_hist = CropHistory(
        id=str(uuid.uuid4()),
        field_id=field.id,
        crop_name=req.current_crop,
        season_name="current_season",
    )
    db.add(crop_hist)

    # 7. Audit log
    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="ONBOARD_FARMER",
        resource_type="user",
        resource_id=user.id,
        user_id=user.id,
        client_ip=request.client.host if request.client else None,
        details={"farm_id": farm.id, "field_id": field.id, "area_ha": area_ha},
    )

    # Issue access token
    token = create_dev_token({
        "sub": user.id,
        "user_id": user.id,
        "role": user.role,
        "country": user.country_iso,
        "name": user.full_name,
        "phone": user.phone_number,
    })

    return OnboardingResponse(
        user_id=user.id,
        farm_id=farm.id,
        field_id=field.id,
        area_hectares=area_ha,
        access_token=token,
    )

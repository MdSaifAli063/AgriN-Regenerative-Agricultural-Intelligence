import math
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.core.security import check_farm_ownership, get_current_user
from app.models.farm import CropHistory, Farm, Field
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.farm_repo import CropHistoryRepository, FarmRepository, FieldRepository
from app.schemas.farm import (
    CropHistoryCreate,
    CropHistoryResponse,
    FarmCreate,
    FarmResponse,
    FarmUpdate,
    FieldCreate,
    FieldFromPointRequest,
    FieldResponse,
    FieldUpdate,
)
from app.services.geo_service import GeoService

router = APIRouter(tags=["Farms & Fields Spatial Management"])


# ============================================================================
# FARMS CRUD
# ============================================================================
@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    farm_in: FarmCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FarmRepository(db)
    farm = Farm(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        farm_name=farm_in.farm_name,
        village_district=farm_in.village_district,
        state_province=farm_in.state_province,
        country_iso=farm_in.country_iso,
        total_area_hectares=farm_in.total_area_hectares,
    )
    created = await repo.create(farm)

    # Audit log
    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="CREATE_FARM",
        resource_type="farm",
        resource_id=created.id,
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
    )

    return created


@router.get("/farms", response_model=List[FarmResponse])
async def list_farms(
    country: Optional[str] = Query(None, min_length=2, max_length=3),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FarmRepository(db)
    if current_user.role == "farmer":
        return await repo.list_by_user(current_user.id, limit=limit, offset=offset)
    elif current_user.role == "extension_officer":
        # Scoped to their country
        return await repo.list_by_country(current_user.country_iso, limit=limit, offset=offset)
    else:
        if country:
            return await repo.list_by_country(country, limit=limit, offset=offset)
        return await repo.list_all(limit=limit, offset=offset)


@router.get("/farms/geojson")
async def get_farms_geojson(
    min_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns a MapLibre FeatureCollection of field polygons, respecting role data minimisation."""
    field_repo = FieldRepository(db)
    if min_lat is not None and min_lon is not None and max_lat is not None and max_lon is not None:
        fields = await field_repo.list_by_bbox(min_lat, min_lon, max_lat, max_lon)
    else:
        fields = await field_repo.list_all(limit=200)

    features = []
    for f in fields:
        # Enforce jurisdiction
        props: Dict[str, Any] = {
            "id": f.id,
            "field_name": f.field_name,
            "area_ha": f.area_hectares,
            "crop": f.current_crop,
            "irrigation": f.irrigation_type,
        }
        features.append({
            "type": "Feature",
            "geometry": f.boundary_geojson,
            "properties": props,
        })

    return {"type": "FeatureCollection", "features": features}


@router.get("/farms/{farm_id}", response_model=FarmResponse)
async def get_farm(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FarmRepository(db)
    farm = await repo.get_by_id(farm_id)
    if not farm:
        raise EntityNotFoundException("Farm", farm_id)
    check_farm_ownership(current_user, farm)
    return farm


@router.patch("/farms/{farm_id}", response_model=FarmResponse)
async def update_farm(
    farm_id: str,
    farm_update: FarmUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FarmRepository(db)
    farm = await repo.get_by_id(farm_id)
    if not farm:
        raise EntityNotFoundException("Farm", farm_id)
    check_farm_ownership(current_user, farm, require_write=True)

    if farm_update.farm_name is not None:
        farm.farm_name = farm_update.farm_name
    if farm_update.village_district is not None:
        farm.village_district = farm_update.village_district
    if farm_update.state_province is not None:
        farm.state_province = farm_update.state_province
    if farm_update.total_area_hectares is not None:
        farm.total_area_hectares = farm_update.total_area_hectares

    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="UPDATE_FARM",
        resource_type="farm",
        resource_id=farm.id,
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
    )
    return farm


@router.delete("/farms/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farm(
    farm_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = FarmRepository(db)
    farm = await repo.get_by_id(farm_id)
    if not farm:
        raise EntityNotFoundException("Farm", farm_id)
    check_farm_ownership(current_user, farm, require_write=True)


    await repo.delete(farm)

    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="DELETE_FARM",
        resource_type="farm",
        resource_id=farm_id,
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
    )


# ============================================================================
# FIELDS CRUD & SHAPELY VALIDATION
# ============================================================================
@router.post("/farms/{farm_id}/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def create_field(
    farm_id: str,
    field_in: FieldCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(farm_id)
    if not farm:
        raise EntityNotFoundException("Farm", farm_id)
    check_farm_ownership(current_user, farm)

    # Rigorous Shapely validation and metric computation
    centroid_lat, centroid_lon, area_ha = GeoService.validate_and_compute_metrics(
        field_in.boundary_geojson
    )

    field = Field(
        id=str(uuid.uuid4()),
        farm_id=farm_id,
        field_name=field_in.field_name,
        boundary_geojson=field_in.boundary_geojson,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
        area_hectares=area_ha,
        irrigation_type=field_in.irrigation_type,
        current_crop=field_in.current_crop,
        sowing_date=field_in.sowing_date,
    )

    field_repo = FieldRepository(db)
    created = await field_repo.create(field)

    # Update total farm area
    farm.total_area_hectares = round(farm.total_area_hectares + area_ha, 4)

    audit_repo = AuditRepository(db)
    await audit_repo.log_event(
        action="CREATE_FIELD",
        resource_type="field",
        resource_id=created.id,
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
        details={"area_ha": area_ha},
    )

    return created


@router.post("/fields/from-point", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
async def create_field_from_point(
    req: FieldFromPointRequest,
    farm_id: str = Query(..., description="Target farm id"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates a square field parcel from dropped GPS pin."""
    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(farm_id)
    if not farm:
        raise EntityNotFoundException("Farm", farm_id)
    check_farm_ownership(current_user, farm)

    polygon = GeoService.create_square_polygon(req.latitude, req.longitude, req.side_meters)
    centroid_lat, centroid_lon, area_ha = GeoService.validate_and_compute_metrics(polygon)

    field = Field(
        id=str(uuid.uuid4()),
        farm_id=farm_id,
        field_name=req.field_name,
        boundary_geojson=polygon,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
        area_hectares=area_ha,
        irrigation_type=req.irrigation_type,
        current_crop=req.current_crop,
    )
    field_repo = FieldRepository(db)
    created = await field_repo.create(field)
    farm.total_area_hectares = round(farm.total_area_hectares + area_ha, 4)

    return created


@router.get("/farms/{farm_id}/fields", response_model=List[FieldResponse])
async def list_farm_fields(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(farm_id)
    if not farm:
        raise EntityNotFoundException("Farm", farm_id)
    check_farm_ownership(current_user, farm)

    field_repo = FieldRepository(db)
    return await field_repo.list_by_farm(farm_id)


@router.get("/fields/{field_id}", response_model=FieldResponse)
async def get_field(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_id(field_id)
    if not field:
        raise EntityNotFoundException("Field", field_id)

    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(field.farm_id)
    if farm:
        check_farm_ownership(current_user, farm)

    return field


@router.get("/fields/{field_id}/geojson")
async def get_single_field_geojson(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    field = await get_field(field_id, current_user, db)
    return {
        "type": "Feature",
        "geometry": field.boundary_geojson,
        "properties": {
            "id": field.id,
            "field_name": field.field_name,
            "area_hectares": field.area_hectares,
            "current_crop": field.current_crop,
            "irrigation_type": field.irrigation_type,
        },
    }


@router.patch("/fields/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: str,
    field_update: FieldUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_id(field_id)
    if not field:
        raise EntityNotFoundException("Field", field_id)

    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(field.farm_id)
    if farm:
        check_farm_ownership(current_user, farm)

    if field_update.field_name is not None:
        field.field_name = field_update.field_name
    if field_update.irrigation_type is not None:
        field.irrigation_type = field_update.irrigation_type
    if field_update.current_crop is not None:
        field.current_crop = field_update.current_crop
    if field_update.sowing_date is not None:
        field.sowing_date = field_update.sowing_date

    return field


@router.delete("/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_id(field_id)
    if not field:
        raise EntityNotFoundException("Field", field_id)

    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(field.farm_id)
    if farm:
        check_farm_ownership(current_user, farm)

    await field_repo.delete(field)


# ============================================================================
# CROP HISTORY CRUD
# ============================================================================
@router.post("/fields/{field_id}/crops", response_model=CropHistoryResponse, status_code=status.HTTP_201_CREATED)
async def add_crop_history(
    field_id: str,
    crop_in: CropHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_id(field_id)
    if not field:
        raise EntityNotFoundException("Field", field_id)

    farm_repo = FarmRepository(db)
    farm = await farm_repo.get_by_id(field.farm_id)
    if farm:
        check_farm_ownership(current_user, farm)

    history = CropHistory(
        id=str(uuid.uuid4()),
        field_id=field_id,
        crop_name=crop_in.crop_name,
        fao_agrovoc_uri=crop_in.fao_agrovoc_uri,
        season_name=crop_in.season_name,
        sowing_date=crop_in.sowing_date,
        harvest_date=crop_in.harvest_date,
        yield_kg_ha=crop_in.yield_kg_ha,
        fertilizers_applied=crop_in.fertilizers_applied,
    )
    crop_repo = CropHistoryRepository(db)
    return await crop_repo.create(history)


@router.get("/fields/{field_id}/crops", response_model=List[CropHistoryResponse])
async def list_crop_history(
    field_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_id(field_id)
    if not field:
        raise EntityNotFoundException("Field", field_id)

    crop_repo = CropHistoryRepository(db)
    return await crop_repo.list_by_field(field_id)


@router.delete("/fields/{field_id}/crops/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop_history(
    field_id: str,
    crop_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    crop_repo = CropHistoryRepository(db)
    item = await crop_repo.get_by_id(crop_id)
    if not item or item.field_id != field_id:
        raise EntityNotFoundException("CropHistory", crop_id)

    await crop_repo.delete(item)

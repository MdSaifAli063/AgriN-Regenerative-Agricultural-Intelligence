from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.farm import CropHistory, Farm, Field
from app.repositories.base import BaseRepository


class FarmRepository(BaseRepository[Farm]):
    def __init__(self, db: AsyncSession):
        super().__init__(Farm, db)

    async def list_by_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Farm]:
        result = await self.db.execute(
            select(Farm).where(Farm.user_id == user_id).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_country(self, country_iso: str, limit: int = 100, offset: int = 0) -> List[Farm]:
        result = await self.db.execute(
            select(Farm).where(Farm.country_iso == country_iso).limit(limit).offset(offset)
        )
        return list(result.scalars().all())


class FieldRepository(BaseRepository[Field]):
    def __init__(self, db: AsyncSession):
        super().__init__(Field, db)

    async def list_by_farm(self, farm_id: str) -> List[Field]:
        result = await self.db.execute(select(Field).where(Field.farm_id == farm_id))
        return list(result.scalars().all())

    async def list_by_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float, limit: int = 100
    ) -> List[Field]:
        result = await self.db.execute(
            select(Field)
            .where(
                Field.centroid_lat >= min_lat,
                Field.centroid_lat <= max_lat,
                Field.centroid_lon >= min_lon,
                Field.centroid_lon <= max_lon,
            )
            .limit(limit)
        )
        return list(result.scalars().all())


class CropHistoryRepository(BaseRepository[CropHistory]):
    def __init__(self, db: AsyncSession):
        super().__init__(CropHistory, db)

    async def list_by_field(self, field_id: str) -> List[CropHistory]:
        result = await self.db.execute(
            select(CropHistory).where(CropHistory.field_id == field_id)
        )
        return list(result.scalars().all())

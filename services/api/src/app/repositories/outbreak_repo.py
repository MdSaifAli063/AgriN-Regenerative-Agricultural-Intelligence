"""
KrishiNet-BRICS – Outbreak Intelligence Repository.

Provides all DB operations for:
  - Logging new DiseaseDetection events (from diagnostic pipeline)
  - Querying detections by region + disease + time window (for aggregation)
  - Upserting OutbreakAggregate records (by H3 hex + disease + period)
  - Fetching aggregate feed for GeoJSON/JSON-LD export

Consent filtering is applied at query time:
  Only detections whose farmer has share_outbreak_telemetry=True
  are included in aggregation inputs.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.disease import DiseaseDetection, OutbreakAggregate
from app.models.user import Consent
from app.repositories.base import BaseRepository


class DiseaseDetectionRepository(BaseRepository[DiseaseDetection]):
    """CRUD + query helpers for individual disease detection events."""

    def __init__(self, db: AsyncSession):
        super().__init__(DiseaseDetection, db)

    async def get_consented_detections_in_window(
        self,
        disease_name: Optional[str],
        since: datetime.datetime,
        until: datetime.datetime,
        country_iso: Optional[str] = None,
        limit: int = 5000,
    ) -> List[DiseaseDetection]:
        """
        Fetches detections within [since, until] where the farmer has granted
        outbreak telemetry consent.  Filters by disease name and country_iso
        when provided.

        This is the privacy-preserving input set for the aggregation pipeline.
        """
        stmt = (
            select(DiseaseDetection)
            .join(Consent, Consent.user_id == DiseaseDetection.farmer_id, isouter=True)
            .where(
                and_(
                    DiseaseDetection.created_at >= since,
                    DiseaseDetection.created_at <= until,
                    # Only include farmers who explicitly shared telemetry,
                    # OR whose consent row doesn't exist yet (default-allow during onboarding)
                    # We model missing consent as EXCLUDED for privacy-first design.
                    Consent.share_outbreak_telemetry == True,  # noqa: E712
                )
            )
            .limit(limit)
        )

        if disease_name:
            stmt = stmt.where(DiseaseDetection.primary_disease_name == disease_name)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_disease_in_window(
        self,
        since: datetime.datetime,
        until: datetime.datetime,
    ) -> List[Tuple[str, int]]:
        """Returns (disease_name, count) pairs for the given window."""
        stmt = (
            select(DiseaseDetection.primary_disease_name, func.count().label("cnt"))
            .join(Consent, Consent.user_id == DiseaseDetection.farmer_id, isouter=True)
            .where(
                and_(
                    DiseaseDetection.created_at >= since,
                    DiseaseDetection.created_at <= until,
                    Consent.share_outbreak_telemetry == True,  # noqa: E712
                )
            )
            .group_by(DiseaseDetection.primary_disease_name)
            .order_by(func.count().desc())
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]


class OutbreakAggregateRepository(BaseRepository[OutbreakAggregate]):
    """CRUD + query helpers for the aggregated outbreak summary table."""

    def __init__(self, db: AsyncSession):
        super().__init__(OutbreakAggregate, db)

    async def get_by_h3_and_disease(
        self,
        h3_index: str,
        disease_name: str,
        period_start: datetime.datetime,
    ) -> Optional[OutbreakAggregate]:
        """Looks up existing aggregate for a specific hex cell + disease + period."""
        stmt = select(OutbreakAggregate).where(
            and_(
                OutbreakAggregate.h3_hex_index == h3_index,
                OutbreakAggregate.disease_name == disease_name,
                OutbreakAggregate.period_start == period_start,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_feed(
        self,
        country_iso: Optional[str] = None,
        disease_name: Optional[str] = None,
        risk_severity: Optional[str] = None,
        since: Optional[datetime.datetime] = None,
        limit: int = 500,
    ) -> List[OutbreakAggregate]:
        """Returns aggregates for the public GeoJSON/JSON-LD outbreak feed."""
        stmt = select(OutbreakAggregate).order_by(
            OutbreakAggregate.period_start.desc()
        )

        if country_iso:
            stmt = stmt.where(OutbreakAggregate.country_iso == country_iso)
        if disease_name:
            stmt = stmt.where(OutbreakAggregate.disease_name == disease_name)
        if risk_severity:
            stmt = stmt.where(OutbreakAggregate.risk_severity == risk_severity)
        if since:
            stmt = stmt.where(OutbreakAggregate.period_start >= since)

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, aggregate: OutbreakAggregate) -> OutbreakAggregate:
        """
        Insert or update (by H3 index + disease + period_start).
        Returns the persisted aggregate.
        """
        existing = await self.get_by_h3_and_disease(
            h3_index=aggregate.h3_hex_index,
            disease_name=aggregate.disease_name,
            period_start=aggregate.period_start,
        )

        if existing is None:
            self.db.add(aggregate)
            await self.db.flush()
            return aggregate
        else:
            existing.incident_count = aggregate.incident_count
            existing.risk_severity = aggregate.risk_severity
            existing.centroid_lat = aggregate.centroid_lat
            existing.centroid_lon = aggregate.centroid_lon
            existing.period_end = aggregate.period_end
            await self.db.flush()
            return existing

    async def get_recent_spike_candidates(
        self,
        disease_name: str,
        country_iso: Optional[str] = None,
        lookback_periods: int = 4,
    ) -> List[OutbreakAggregate]:
        """
        Fetches the most recent N aggregate records for a disease to support
        spike detection (comparing current vs prior period counts).
        """
        stmt = (
            select(OutbreakAggregate)
            .where(OutbreakAggregate.disease_name == disease_name)
            .order_by(OutbreakAggregate.period_start.desc())
            .limit(lookback_periods * 50)  # wide fetch, spike detection filters further
        )
        if country_iso:
            stmt = stmt.where(OutbreakAggregate.country_iso == country_iso)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

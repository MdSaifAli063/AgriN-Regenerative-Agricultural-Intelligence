"""
KrishiNet-BRICS - Inbound Federation Sync Service.
Pulls partner BRICS nodes' published aggregates and model cards through the Registry
and stores them into segregated external_* tables.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.federation import (
    ExternalClimateSignature,
    ExternalImpactMetric,
    ExternalModelCard,
    ExternalOutbreakAggregate,
)
from app.services.service_guard import ExternalServiceGuard

logger = logging.getLogger("krishinet.federation.sync")


class InboundSyncService:
    """
    Synchronizes external BRICS data into local segregated external_* tables.
    """

    def __init__(self, db: AsyncSession, registry_url: str):
        self.db = db
        self.registry_url = registry_url.rstrip("/")
        self.guard = ExternalServiceGuard(
            service_name="brics-registry-inbound-sync",
            timeout_seconds=6.0,
            max_retries=2,
        )

    async def sync_external_outbreaks(self) -> int:
        """
        Pulls transboundary outbreak alerts and populates external_outbreak_aggregates.
        """
        async def _fetch():
            if settings.DEMO_MODE:
                # Return synthetic multi-country BRICS outbreak features
                return [
                    {
                        "origin_country_iso": "BRA",
                        "origin_node_id": "node-bra-embrapa-01",
                        "h3_index": "86618840fffffff",
                        "disease_label": "soybean_rust",
                        "disease_name": "Asian Soybean Rust (Phakopsora pachyrhizi)",
                        "reported_cases": 42,
                        "risk_severity": "critical",
                        "is_spike": True,
                        "period_start": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7),
                        "period_end": datetime.datetime.now(datetime.timezone.utc),
                    },
                    {
                        "origin_country_iso": "ZAF",
                        "origin_node_id": "node-zaf-arc-01",
                        "h3_index": "86618843fffffff",
                        "disease_label": "maize_gray_leaf_spot",
                        "disease_name": "Gray Leaf Spot (Cercospora zeae-maydis)",
                        "reported_cases": 19,
                        "risk_severity": "medium",
                        "is_spike": False,
                        "period_start": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7),
                        "period_end": datetime.datetime.now(datetime.timezone.utc),
                    },
                ]

            endpoint = f"{self.registry_url}/registry/v1/outbreaks/feed"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint)
                resp.raise_for_status()
                return resp.json().get("features", [])

        items = await self.guard.execute(_fetch)
        count = 0

        for item in items:
            record = ExternalOutbreakAggregate(
                origin_country_iso=item.get("origin_country_iso", "GLOBAL"),
                origin_node_id=item.get("origin_node_id", "peer-node"),
                h3_index=item.get("h3_index", "86618840fffffff"),
                disease_label=item.get("disease_label", "unknown"),
                disease_name=item.get("disease_name", "Unknown Disease"),
                reported_cases=item.get("reported_cases", 0),
                risk_severity=item.get("risk_severity", "medium"),
                is_spike=item.get("is_spike", False),
                period_start=item.get("period_start", datetime.datetime.now(datetime.timezone.utc)),
                period_end=item.get("period_end", datetime.datetime.now(datetime.timezone.utc)),
            )
            self.db.add(record)
            count += 1

        await self.db.commit()
        return count

    async def sync_external_models(self) -> int:
        """
        Pulls published model cards from partner nodes into external_model_cards.
        """
        async def _fetch():
            if settings.DEMO_MODE:
                return [
                    {
                        "origin_node_id": "node-bra-embrapa-01",
                        "origin_country_iso": "BRA",
                        "model_name": "MobileNetV3-Cerrado-Soybean-Int8",
                        "version_tag": "1.2.0",
                        "task_type": "disease_detection",
                        "crop_coverage": ["Soybean", "Maize"],
                        "accuracy_score": 0.924,
                        "f1_score": 0.918,
                        "quantization": "int8",
                        "size_mb": 4.1,
                        "license_type": "Apache-2.0",
                        "weights_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "download_url": "https://models.embrapa.br/weights/mobilenetv3-soybean.onnx",
                    }
                ]

            endpoint = f"{self.registry_url}/registry/v1/models"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint)
                resp.raise_for_status()
                return resp.json()

        models = await self.guard.execute(_fetch)
        count = 0

        for m in models:
            record = ExternalModelCard(
                origin_node_id=m["origin_node_id"],
                origin_country_iso=m["origin_country_iso"],
                model_name=m["model_name"],
                version_tag=m["version_tag"],
                task_type=m["task_type"],
                crop_coverage=m["crop_coverage"],
                accuracy_score=m["accuracy_score"],
                f1_score=m.get("f1_score"),
                quantization=m.get("quantization", "int8"),
                size_mb=m["size_mb"],
                license_type=m["license_type"],
                weights_sha256=m["weights_sha256"],
                download_url=m["download_url"],
                status="candidate",
            )
            self.db.add(record)
            count += 1

        await self.db.commit()
        return count

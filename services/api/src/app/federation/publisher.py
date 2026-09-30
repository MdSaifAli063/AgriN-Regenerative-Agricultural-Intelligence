"""
KrishiNet-BRICS - Outbound Federation Publisher.
Publishes anonymized outbreak feeds, model cards, impact figures, and climate signatures to the BRICS Commons Registry.
All operations are wrapped with ExternalServiceGuard and validated by the Sovereign Egress Gate.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.federation.egress_gate import EgressGate
from app.federation.identity import NodeIdentity
from app.services.service_guard import ExternalServiceGuard

logger = logging.getLogger("krishinet.federation.publisher")


class OutboundPublisher:
    """
    Manages publication of sovereign node data to the BRICS Commons Registry.
    """

    def __init__(self, db: AsyncSession, identity: NodeIdentity, registry_url: str):
        self.db = db
        self.identity = identity
        self.registry_url = registry_url.rstrip("/")
        self.egress_gate = EgressGate(db)

        # Service Guard resilience wrapper
        self.guard = ExternalServiceGuard(
            service_name="brics-registry-publisher",
            timeout_seconds=5.0,
            max_retries=2,
        )

    async def publish_outbreaks(
        self,
        features: List[Dict[str, Any]],
        is_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Validates through Egress Gate (k-anonymity, coordinate precision) and publishes to Registry.
        """
        payload = {
            "type": "FeatureCollection",
            "country_iso": settings.NODE_COUNTRY,
            "node_id": self.identity.node_id,
            "features": features,
        }

        # 1. Sovereign Egress Gate evaluation & audit logging
        passed, msg, summary = await self.egress_gate.evaluate_and_record(
            destination_type="registry",
            destination_id="brics-commons-registry-01",
            scope="outbreak_aggregates",
            payload=payload,
            is_dry_run=is_dry_run,
        )

        if is_dry_run or not passed:
            return {"status": "dry_run" if is_dry_run else "blocked", "message": msg, "summary": summary}

        # 2. Network dispatch behind ExternalServiceGuard
        async def _send():
            if settings.DEMO_MODE:
                return {"status": "published", "destination": "registry", "features_count": len(features)}

            endpoint = f"{self.registry_url}/registry/v1/outbreaks"
            body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            headers = self.identity.create_signed_headers(body_bytes)
            headers["Content-Type"] = "application/json"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, content=body_bytes, headers=headers)
                resp.raise_for_status()
                return resp.json()

        return await self.guard.execute(_send)

    async def publish_impact(
        self,
        impact_data: Dict[str, Any],
        is_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Publishes macro regenerative impact figures.
        """
        passed, msg, summary = await self.egress_gate.evaluate_and_record(
            destination_type="registry",
            destination_id="brics-commons-registry-01",
            scope="impact_aggregates",
            payload=impact_data,
            is_dry_run=is_dry_run,
        )

        if is_dry_run or not passed:
            return {"status": "dry_run" if is_dry_run else "blocked", "message": msg, "summary": summary}

        async def _send():
            if settings.DEMO_MODE:
                return {"status": "published", "destination": "registry", "impact": impact_data}

            endpoint = f"{self.registry_url}/registry/v1/impact"
            body_bytes = json.dumps(impact_data, sort_keys=True).encode("utf-8")
            headers = self.identity.create_signed_headers(body_bytes)
            headers["Content-Type"] = "application/json"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, content=body_bytes, headers=headers)
                resp.raise_for_status()
                return resp.json()

        return await self.guard.execute(_send)

    async def publish_climate_signatures(
        self,
        signatures: List[Dict[str, Any]],
        is_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Publishes coarse regional climate vectors for analogue twin matching.
        """
        payload = {
            "country_iso": settings.NODE_COUNTRY,
            "node_id": self.identity.node_id,
            "signatures": signatures,
        }

        passed, msg, summary = await self.egress_gate.evaluate_and_record(
            destination_type="registry",
            destination_id="brics-commons-registry-01",
            scope="climate_signatures",
            payload=payload,
            is_dry_run=is_dry_run,
        )

        if is_dry_run or not passed:
            return {"status": "dry_run" if is_dry_run else "blocked", "message": msg, "summary": summary}

        async def _send():
            if settings.DEMO_MODE:
                return {"status": "published", "destination": "registry", "signatures_count": len(signatures)}

            endpoint = f"{self.registry_url}/registry/v1/analogues"
            body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            headers = self.identity.create_signed_headers(body_bytes)
            headers["Content-Type"] = "application/json"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(endpoint, content=body_bytes, headers=headers)
                resp.raise_for_status()
                return resp.json()

        return await self.guard.execute(_send)

"""
KrishiNet-BRICS - Sovereign Egress Gate.
Guarantees that 0 farmer PII, 0 cadastral boundaries, and 0 raw leaf photos leave the national boundary.
Every outbound federation payload (outbreak feeds, model cards, climate signatures, impact aggregates)
MUST pass this gate before network transmission.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.federation import EgressAuditLog, FederationAgreement

logger = logging.getLogger("krishinet.federation.egress")

# Permitted Outbound Scopes
ALLOWED_EGRESS_SCOPES = {
    "heartbeat",
    "outbreak_aggregates",
    "impact_aggregates",
    "model_exchange",
    "climate_signatures",
}

# Strict Denylist: Any presence of these keys immediately rejects the payload
DENIED_PII_KEYS = {
    "farmer_id",
    "farmer_name",
    "full_name",
    "phone_number",
    "phone",
    "national_id",
    "aadhar",
    "cpf",
    "tax_id",
    "email",
    "address",
    "cadastre",
    "boundary",
    "polygon",
    "field_polygon",
    "farm_boundary",
    "raw_image",
    "image_bytes",
    "leaf_photo",
    "photo_bytes",
}

MAX_COORDINATE_DECIMALS = 2  # Max 2 decimals allowed (~1.1km coarse resolution)
MIN_K_ANONYMITY_THRESHOLD = 5  # Cell aggregation suppression threshold


class EgressGateViolation(Exception):
    def __init__(self, message: str, violation_type: str = "PII_OR_POLICY_VIOLATION"):
        super().__init__(message)
        self.message = message
        self.violation_type = violation_type


def _count_decimals(val: float) -> int:
    s = f"{val:.10f}".rstrip("0")
    if "." not in s:
        return 0
    return len(s.split(".")[1])


def scan_payload_for_leaks(data: Any, path: str = "") -> None:
    """
    Recursively validates that data contains no denylisted keys and no high-precision coordinates.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            curr_path = f"{path}.{k}" if path else str(k)
            lower_k = str(k).lower()

            # Denylist check
            if (
                lower_k in DENIED_PII_KEYS
                or "farmer_id" in lower_k
                or "farmer_name" in lower_k
                or "cadastre" in lower_k
                or "boundary" in lower_k
                or "polygon" in lower_k
            ):
                raise EgressGateViolation(
                    f"Forbidden PII / Cadastre field '{curr_path}' detected in outbound payload.",
                    violation_type="PII_LEAK_PREVENTION",
                )

            # Coordinate check
            if lower_k in ["lat", "latitude", "lon", "lng", "longitude", "coord", "coordinates"]:
                if isinstance(v, (int, float)):
                    decs = _count_decimals(float(v))
                    if decs > MAX_COORDINATE_DECIMALS:
                        raise EgressGateViolation(
                            f"Coordinate '{curr_path}' has precision {decs} decimals (> {MAX_COORDINATE_DECIMALS}). "
                            "National sovereignty rules forbid transmitting coordinates finer than 2 decimal places.",
                            violation_type="FINE_COORDINATE_LEAK",
                        )
                elif isinstance(v, (list, tuple)):
                    for idx, c in enumerate(v):
                        if isinstance(c, (int, float)):
                            decs = _count_decimals(float(c))
                            if decs > MAX_COORDINATE_DECIMALS:
                                raise EgressGateViolation(
                                    f"Coordinate array '{curr_path}[{idx}]' has precision {decs} decimals "
                                    f"(> {MAX_COORDINATE_DECIMALS}).",
                                    violation_type="FINE_COORDINATE_LEAK",
                                )

            scan_payload_for_leaks(v, curr_path)

    elif isinstance(data, list):
        for idx, item in enumerate(data):
            scan_payload_for_leaks(item, f"{path}[{idx}]")

    elif isinstance(data, (int, float)):
        last_k = path.split(".")[-1].split("[")[0].lower()
        if last_k in ["lat", "latitude", "lon", "lng", "longitude"]:
            decs = _count_decimals(float(data))
            if decs > MAX_COORDINATE_DECIMALS:
                raise EgressGateViolation(
                    f"Coordinate at '{path}' has precision {decs} decimals (> {MAX_COORDINATE_DECIMALS}).",
                    violation_type="FINE_COORDINATE_LEAK",
                )


def check_k_anonymity_suppression(scope: str, payload: Any) -> None:
    """
    Suppresses any aggregated cell with fewer than MIN_K_ANONYMITY_THRESHOLD farmers/cases.
    """
    if scope == "outbreak_aggregates":
        features = []
        if isinstance(payload, dict):
            features = payload.get("features", [])
        elif isinstance(payload, list):
            features = payload

        for idx, feat in enumerate(features):
            props = feat.get("properties", {}) if isinstance(feat, dict) else {}
            cases = props.get("reported_cases", 0)
            if cases < MIN_K_ANONYMITY_THRESHOLD:
                raise EgressGateViolation(
                    f"Outbreak cluster feature [{idx}] reports {cases} cases (< k-anonymity threshold {MIN_K_ANONYMITY_THRESHOLD}). "
                    "Must be suppressed or merged to prevent re-identification.",
                    violation_type="K_ANONYMITY_VIOLATION",
                )

    elif scope == "impact_aggregates":
        if isinstance(payload, dict):
            farmers = payload.get("farmers_reached", 0)
            if farmers < MIN_K_ANONYMITY_THRESHOLD:
                raise EgressGateViolation(
                    f"Impact aggregation reports {farmers} farmers (< k-anonymity threshold {MIN_K_ANONYMITY_THRESHOLD}).",
                    violation_type="K_ANONYMITY_VIOLATION",
                )


class EgressGate:
    """
    Central gatekeeper managing validation, data-sharing agreement checks,
    dry-run reports, and cryptographic audit log recording.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_agreement(
        self,
        destination_id: str,
        scope: str,
    ) -> bool:
        """
        Verifies that an active bilateral or multilateral agreement exists for the target scope.
        The Central Registry is exempt for heartbeat, model_exchange, and aggregated feeds.
        """
        if "registry" in destination_id.lower():
            return True

        stmt = select(FederationAgreement).where(
            FederationAgreement.status == "active",
            (FederationAgreement.peer_node_id == destination_id) | (FederationAgreement.peer_node_id == "ALL_BRICS"),
        )
        res = await self.db.execute(stmt)
        agreements = res.scalars().all()

        for a in agreements:
            if scope in a.scopes or "all" in a.scopes:
                return True

        return False

    async def evaluate_and_record(
        self,
        destination_type: str,
        destination_id: str,
        scope: str,
        payload: Any,
        is_dry_run: bool = False,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Processes an outbound payload through all 4 sovereign checks:
        1. Scope allow-list check
        2. Agreement verification
        3. PII & fine coordinate scanning
        4. k-Anonymity threshold check
        Records immutable EgressAuditLog entry.
        """
        body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(body_bytes).hexdigest()

        summary: Dict[str, Any] = {
            "scope": scope,
            "bytes_length": len(body_bytes),
            "destination": destination_id,
        }

        if isinstance(payload, dict):
            summary["keys_count"] = len(payload)
            if "features" in payload and isinstance(payload["features"], list):
                summary["feature_count"] = len(payload["features"])

        rejection_reason = None
        passed = True

        # Check 1: Scope allow-list
        if scope not in ALLOWED_EGRESS_SCOPES:
            passed = False
            rejection_reason = f"Scope '{scope}' is not in sovereign allow-list."

        # Check 2: Active Agreement
        if passed:
            has_agreement = await self.verify_agreement(destination_id, scope)
            if not has_agreement:
                passed = False
                rejection_reason = f"No active data sharing agreement with '{destination_id}' for scope '{scope}'."

        # Check 3: Privacy & Coordinates
        if passed:
            try:
                scan_payload_for_leaks(payload)
            except EgressGateViolation as e:
                passed = False
                rejection_reason = e.message

        # Check 4: k-Anonymity
        if passed:
            try:
                check_k_anonymity_suppression(scope, payload)
            except EgressGateViolation as e:
                passed = False
                rejection_reason = e.message

        # Record Egress Audit Log
        audit_entry = EgressAuditLog(
            destination_type=destination_type,
            destination_id=destination_id,
            scope=scope,
            payload_hash=payload_hash,
            payload_summary=summary,
            is_dry_run=is_dry_run,
            passed_egress_gate=passed,
            rejection_reason=rejection_reason,
        )
        self.db.add(audit_entry)
        await self.db.commit()

        if not passed and not is_dry_run:
            logger.error(f"[EGRESS_GATE_BLOCKED] Scope: {scope} | Destination: {destination_id} | Reason: {rejection_reason}")
            raise EgressGateViolation(rejection_reason or "Egress Gate check failed.")

        return passed, rejection_reason or "Passed all sovereign egress gates.", summary

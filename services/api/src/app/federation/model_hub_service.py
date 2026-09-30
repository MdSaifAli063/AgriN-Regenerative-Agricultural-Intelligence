"""
Part 7D – Model Hub Service.

Responsibilities:
  1. Register a new model version into the Hub catalog (candidate state).
  2. Ed25519-sign the model card JSON using the node identity key.
  3. Verify an incoming model card signature from a peer node.
  4. Run the Promotion Gate (accuracy / fairness / latency thresholds).
  5. Promote or reject a candidate entry (immutable event logged).
  6. Generate presigned MinIO download URLs (time-limited, HMAC-protected).
  7. List the Hub catalog with optional filtering.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.federation.identity import NodeIdentity
from app.models.model_hub import ModelHubEntry, ModelEvaluation, ModelPromotionEvent

logger = logging.getLogger("krishinet.model_hub")


# ── Promotion Gate Thresholds ────────────────────────────────────────────────
GATE_MIN_ACCURACY: float = 0.80          # 80 % overall accuracy
GATE_MIN_F1_MACRO: float = 0.75          # 75 % macro F1
GATE_MIN_SUBGROUP_F1: float = 0.65       # 65 % worst-crop subgroup F1
GATE_MAX_PARITY_GAP: float = 0.15        # 15 % max demographic parity gap
GATE_MAX_P95_LATENCY_MS: float = 250.0   # 250 ms p95 latency on reference edge device
GATE_MAX_RAM_MB: float = 128.0           # 128 MB peak RAM


class PromotionGate:
    """Evaluates whether a ModelEvaluation meets the Hub promotion thresholds."""

    @staticmethod
    def check(ev: ModelEvaluation) -> tuple[bool, Dict[str, Any]]:
        """Return (passed, detail_dict)."""
        detail: Dict[str, Any] = {}
        passed = True

        checks = [
            ("accuracy", ev.accuracy, ">=", GATE_MIN_ACCURACY),
            ("f1_macro", ev.f1_macro, ">=", GATE_MIN_F1_MACRO),
            ("min_subgroup_f1", ev.min_subgroup_f1, ">=", GATE_MIN_SUBGROUP_F1),
            ("max_demographic_parity_gap", ev.max_demographic_parity_gap, "<=", GATE_MAX_PARITY_GAP),
        ]

        for name, val, op, threshold in checks:
            ok = (val >= threshold) if op == ">=" else (val <= threshold)
            detail[name] = {"value": val, "threshold": threshold, "op": op, "pass": ok}
            if not ok:
                passed = False

        # Latency checks (optional – only fail if data provided)
        if ev.inference_ms_p95 is not None:
            ok = ev.inference_ms_p95 <= GATE_MAX_P95_LATENCY_MS
            detail["inference_ms_p95"] = {
                "value": ev.inference_ms_p95,
                "threshold": GATE_MAX_P95_LATENCY_MS,
                "op": "<=",
                "pass": ok,
            }
            if not ok:
                passed = False

        if ev.peak_ram_mb is not None:
            ok = ev.peak_ram_mb <= GATE_MAX_RAM_MB
            detail["peak_ram_mb"] = {
                "value": ev.peak_ram_mb,
                "threshold": GATE_MAX_RAM_MB,
                "op": "<=",
                "pass": ok,
            }
            if not ok:
                passed = False

        detail["fairness_pass"] = ev.fairness_pass
        if not ev.fairness_pass:
            passed = False

        return passed, detail


class ModelHubService:
    """Model Hub: catalog, signing, presigned URLs, and promotion lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._identity: Optional[NodeIdentity] = None

    def _get_identity(self) -> NodeIdentity:
        if self._identity is None:
            from pathlib import Path
            keys_dir = Path(".node_keys")
            self._identity = NodeIdentity.load_or_create(keys_dir, settings.NODE_ID)
        return self._identity

    # ── Signing ────────────────────────────────────────────────────────────

    def sign_card_json(self, card_dict: Dict[str, Any]) -> str:
        """
        Sign the canonical JSON of a model card dict using the node's Ed25519 key.
        Returns hex-encoded signature (128 hex chars for Ed25519's 64-byte sig).
        """
        identity = self._get_identity()
        canonical = json.dumps(card_dict, sort_keys=True, separators=(",", ":")).encode()
        sig_b64 = identity.sign_message(canonical)           # base64-encoded
        sig_bytes = __import__('base64').b64decode(sig_b64)
        return sig_bytes.hex()

    @staticmethod
    def verify_card_signature(
        card_dict: Dict[str, Any],
        signature_hex: str,
        public_key_pem: str,
    ) -> bool:
        """
        Verify an Ed25519 signature over card_dict using the provided PEM public key.
        Returns True if valid, False otherwise.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey as _PK
            pub_key = serialization.load_pem_public_key(public_key_pem.encode())
            canonical = json.dumps(card_dict, sort_keys=True, separators=(",", ":")).encode()
            sig_bytes = bytes.fromhex(signature_hex)
            pub_key.verify(sig_bytes, canonical)  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            logger.warning(f"Model card signature verification failed: {exc}")
            return False

    # ── Presigned Download URLs ────────────────────────────────────────────

    @staticmethod
    def generate_presigned_url(
        object_key: str,
        expires_seconds: int = 3600,
        bucket: Optional[str] = None,
    ) -> str:
        """
        Generate a time-limited presigned MinIO download URL.
        Falls back to a simulated URL if MinIO is unavailable (dev mode).
        """
        target_bucket = bucket or settings.MINIO_BUCKET_NAME
        try:
            from minio import Minio
            from datetime import timedelta

            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_SECURE,
            )
            url = client.presigned_get_object(
                target_bucket,
                object_key,
                expires=timedelta(seconds=expires_seconds),
            )
            return url
        except Exception as exc:
            logger.warning(f"MinIO presign failed ({exc}); returning simulated URL.")
            # Dev fallback: deterministic signed URL structure (HMAC would be added in prod)
            return (
                f"http://{settings.MINIO_ENDPOINT}/{target_bucket}/{object_key}"
                f"?X-Amz-Expires={expires_seconds}&X-Amz-SignedHeaders=host"
                f"&X-Amz-Signature=devmode"
            )

    # ── Catalog CRUD ───────────────────────────────────────────────────────

    async def register_entry(
        self,
        model_card_id: str,
        bucket: str,
        object_key: str,
        size_bytes: int,
        weights_sha256: str,
        task_type: str,
        crop_coverage: List[str],
        card_json: Dict[str, Any],
        quantization: str = "int8",
        framework: str = "tflite",
        license_type: str = "Apache-2.0",
    ) -> ModelHubEntry:
        """Register a new candidate entry in the Hub catalog, auto-signing the card."""
        signature_hex = self.sign_card_json(card_json)
        identity = self._get_identity()

        entry = ModelHubEntry(
            id=str(uuid.uuid4()),
            model_card_id=model_card_id,
            node_id=settings.NODE_ID,
            country_iso=settings.NODE_COUNTRY,
            status="candidate",
            bucket=bucket,
            object_key=object_key,
            size_bytes=size_bytes,
            weights_sha256=weights_sha256,
            card_json=card_json,
            card_signature_hex=signature_hex,
            card_signed_by_node=settings.NODE_ID,
            quantization=quantization,
            framework=framework,
            task_type=task_type,
            crop_coverage=crop_coverage,
            license_type=license_type,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        logger.info(f"Registered Hub entry {entry.id} for card {model_card_id}")
        return entry

    async def submit_evaluation(
        self,
        hub_entry_id: str,
        eval_dataset: str,
        accuracy: float,
        f1_macro: float,
        precision: float,
        recall: float,
        min_subgroup_f1: float,
        max_demographic_parity_gap: float,
        fairness_pass: bool,
        inference_ms_p50: Optional[float] = None,
        inference_ms_p95: Optional[float] = None,
        peak_ram_mb: Optional[float] = None,
        eval_commit_hash: Optional[str] = None,
    ) -> ModelEvaluation:
        """Record an evaluation run and run the Promotion Gate."""
        # Temporary eval object (not yet persisted) for gate check
        ev = ModelEvaluation(
            id=str(uuid.uuid4()),
            hub_entry_id=hub_entry_id,
            eval_dataset=eval_dataset,
            eval_node_id=settings.NODE_ID,
            accuracy=accuracy,
            f1_macro=f1_macro,
            precision=precision,
            recall=recall,
            min_subgroup_f1=min_subgroup_f1,
            max_demographic_parity_gap=max_demographic_parity_gap,
            fairness_pass=fairness_pass,
            inference_ms_p50=inference_ms_p50,
            inference_ms_p95=inference_ms_p95,
            peak_ram_mb=peak_ram_mb,
            eval_commit_hash=eval_commit_hash,
        )
        gate_passed, gate_detail = PromotionGate.check(ev)
        ev.gate_passed = gate_passed
        ev.gate_detail = gate_detail

        self.db.add(ev)
        await self.db.commit()
        await self.db.refresh(ev)
        logger.info(
            f"Evaluation {ev.id} for hub_entry={hub_entry_id}: "
            f"gate_passed={gate_passed}"
        )
        return ev

    async def promote(
        self,
        hub_entry_id: str,
        reviewer_role: str,
        rationale: str,
        reviewer_country_iso: str,
    ) -> ModelHubEntry:
        """Promote a candidate model to active status (requires gate pass)."""
        entry = await self._get_entry_or_raise(hub_entry_id)

        # Verify at least one gate-passing evaluation exists
        result = await self.db.execute(
            select(ModelEvaluation).where(
                ModelEvaluation.hub_entry_id == hub_entry_id,
                ModelEvaluation.gate_passed == True,  # noqa: E712
            ).limit(1)
        )
        passing_eval = result.scalar_one_or_none()
        if passing_eval is None:
            raise ValueError(
                f"Cannot promote hub entry {hub_entry_id}: no gate-passing evaluation found."
            )

        prev_status = entry.status
        entry.status = "promoted"
        entry.promoted_at = datetime.now(timezone.utc)

        # Sign the promotion event
        event_dict = {
            "hub_entry_id": hub_entry_id,
            "action": "promote",
            "reviewer_node_id": settings.NODE_ID,
            "reviewer_country_iso": reviewer_country_iso,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sig_hex = self.sign_card_json(event_dict)

        event = ModelPromotionEvent(
            hub_entry_id=hub_entry_id,
            action="promote",
            reviewer_node_id=settings.NODE_ID,
            reviewer_country_iso=reviewer_country_iso,
            reviewer_role=reviewer_role,
            rationale=rationale,
            signature_hex=sig_hex,
            previous_status=prev_status,
            new_status="promoted",
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(entry)
        logger.info(f"Hub entry {hub_entry_id} promoted by {settings.NODE_ID}")
        return entry

    async def reject(
        self,
        hub_entry_id: str,
        reviewer_role: str,
        rationale: str,
        reviewer_country_iso: str,
    ) -> ModelHubEntry:
        """Reject a candidate or promoted model."""
        entry = await self._get_entry_or_raise(hub_entry_id)
        prev_status = entry.status
        entry.status = "rejected"

        event_dict = {
            "hub_entry_id": hub_entry_id,
            "action": "reject",
            "reviewer_node_id": settings.NODE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sig_hex = self.sign_card_json(event_dict)

        event = ModelPromotionEvent(
            hub_entry_id=hub_entry_id,
            action="reject",
            reviewer_node_id=settings.NODE_ID,
            reviewer_country_iso=reviewer_country_iso,
            reviewer_role=reviewer_role,
            rationale=rationale,
            signature_hex=sig_hex,
            previous_status=prev_status,
            new_status="rejected",
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(entry)
        logger.info(f"Hub entry {hub_entry_id} rejected by {settings.NODE_ID}")
        return entry

    async def deprecate(
        self,
        hub_entry_id: str,
        reviewer_role: str,
        rationale: str,
        reviewer_country_iso: str,
    ) -> ModelHubEntry:
        """Deprecate an active (promoted) model."""
        entry = await self._get_entry_or_raise(hub_entry_id)
        prev_status = entry.status
        entry.status = "deprecated"
        entry.deprecated_at = datetime.now(timezone.utc)

        event_dict = {
            "hub_entry_id": hub_entry_id,
            "action": "deprecate",
            "reviewer_node_id": settings.NODE_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sig_hex = self.sign_card_json(event_dict)

        event = ModelPromotionEvent(
            hub_entry_id=hub_entry_id,
            action="deprecate",
            reviewer_node_id=settings.NODE_ID,
            reviewer_country_iso=reviewer_country_iso,
            reviewer_role=reviewer_role,
            rationale=rationale,
            signature_hex=sig_hex,
            previous_status=prev_status,
            new_status="deprecated",
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_catalog(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        country_iso: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ModelHubEntry]:
        """Return Hub catalog entries with optional filtering."""
        q = select(ModelHubEntry)
        if status:
            q = q.where(ModelHubEntry.status == status)
        if task_type:
            q = q.where(ModelHubEntry.task_type == task_type)
        if country_iso:
            q = q.where(ModelHubEntry.country_iso == country_iso)
        q = q.order_by(ModelHubEntry.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_entry(self, hub_entry_id: str) -> Optional[ModelHubEntry]:
        result = await self.db.execute(
            select(ModelHubEntry).where(ModelHubEntry.id == hub_entry_id)
        )
        return result.scalar_one_or_none()

    async def get_evaluations(self, hub_entry_id: str) -> List[ModelEvaluation]:
        result = await self.db.execute(
            select(ModelEvaluation)
            .where(ModelEvaluation.hub_entry_id == hub_entry_id)
            .order_by(ModelEvaluation.evaluated_at.desc())
        )
        return list(result.scalars().all())

    async def get_promotion_history(self, hub_entry_id: str) -> List[ModelPromotionEvent]:
        result = await self.db.execute(
            select(ModelPromotionEvent)
            .where(ModelPromotionEvent.hub_entry_id == hub_entry_id)
            .order_by(ModelPromotionEvent.event_at.desc())
        )
        return list(result.scalars().all())

    # ── Internal ───────────────────────────────────────────────────────────

    async def _get_entry_or_raise(self, hub_entry_id: str) -> ModelHubEntry:
        entry = await self.get_entry(hub_entry_id)
        if entry is None:
            raise ValueError(f"Hub entry '{hub_entry_id}' not found.")
        return entry

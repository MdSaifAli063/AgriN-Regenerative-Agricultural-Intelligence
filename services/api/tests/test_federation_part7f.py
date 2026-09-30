"""
Phase 7F End-to-End Federation Integration Test Suite.
Validates the complete 8-step sovereign federation lifecycle:
  1. Multi-Node Sovereign Identity & Passport Verification (IND, BRA, ZAF)
  2. Sovereign Egress Gate (4-Stage validation: Zero-PII, k-anonymity, coordinate truncation)
  3. Cross-Border Climate-Analogue Matching with Hemispheric Season Alignment
  4. Sovereign Model Hub with Ed25519 Signed Cards and Verification
  5. Flower Federated Learning Simulation with DP Noise & Byzantine Defense
  6. Kantara-Compliant Consent Receipts with Ed25519 Signatures
  7. Append-Only Cryptographic Consent Hash Chain Integrity
  8. Tamper-Evidence & Fraud Detection on Corrupted Blocks
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "src"))
sys.path.insert(0, str(REPO_ROOT / "services" / "registry" / "src"))

from app.db.base import Base
from app.federation.identity import NodeIdentity, get_node_identity
from app.federation.egress_gate import (
    EgressGate,
    EgressGateViolation,
    scan_payload_for_leaks,
    check_k_anonymity_suppression,
)
from app.federation.climate_analogue import (
    ClimateAnalogueMatcher,
    ClimateProfile,
    SEEDED_BRICS_PROFILES,
)
from app.models.model_hub import ModelHubEntry
from app.federation.consent_manager import (
    ConsentLedger,
    ConsentManager,
    ConsentScopeUpdate,
)
from app.federation.flower.simulator import FederatedSimulator

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def temp_keys_dir():
    d = tempfile.mkdtemp(prefix="test_keys_7f_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def temp_ledger_file(tmp_path):
    return tmp_path / "test_consent_ledger_7f.json"


class TestPhase7FE2EFederation:
    def test_step_1_multi_node_sovereign_identity_and_passports(self, temp_keys_dir):
        """Step 1: Verify independent Ed25519 identities for India, Brazil, and South Africa."""
        node_ind = NodeIdentity.load_or_create(temp_keys_dir, "node-ind-01", country_code="IND")
        node_bra = NodeIdentity.load_or_create(temp_keys_dir, "node-bra-01", country_code="BRA")
        node_zaf = NodeIdentity.load_or_create(temp_keys_dir, "node-zaf-01", country_code="ZAF")

        assert node_ind.node_id != node_bra.node_id
        assert node_ind.country_code == "IND"
        assert node_bra.country_code == "BRA"
        assert node_zaf.country_code == "ZAF"

        # Verify cross-node signature verification
        test_payload = b"BRICS_COMMON_METRICS_TELEMETRY"
        sig_ind = node_ind.sign(test_payload)
        assert node_ind.verify_signature(test_payload, sig_ind)
        # Verifying with another node's key must fail
        assert not node_bra.verify_signature(test_payload, sig_ind)

    def test_step_2_sovereign_egress_gate_validation(self):
        """Step 2: Verify 4-stage egress validation enforcing 0 PII, coordinate coarsening, and k-anonymity."""
        # A. Valid anonymized outbreak payload passes
        valid_payload = {
            "features": [
                {
                    "geometry": {"coordinates": [78.59, 20.74]},  # 2 decimal places max
                    "properties": {"disease": "rice_blast", "reported_cases": 14},
                }
            ]
        }
        # Must not raise
        scan_payload_for_leaks(valid_payload)
        check_k_anonymity_suppression("outbreak_aggregates", valid_payload)

        # B. Malicious payload leaking PII (Phone number & Farmer Name) must raise EgressGateViolation
        pii_payload = {
            "h3_index": "86618844fffffff",
            "farmer_phone": "+919876543210",
            "farmer_name": "Ramesh Patel",
        }
        with pytest.raises(EgressGateViolation) as exc_pii:
            scan_payload_for_leaks(pii_payload)
        assert "PII" in str(exc_pii.value) or "farmer" in str(exc_pii.value).lower()

        # C. High-precision GPS coordinates (> 2 decimal places) must be rejected to protect farmer fields
        fine_coord_payload = {
            "coordinates": [78.59821, 20.74533],  # 5 decimals -> invasive precision
        }
        with pytest.raises(EgressGateViolation) as exc_coord:
            scan_payload_for_leaks(fine_coord_payload)
        assert "coordinate" in str(exc_coord.value).lower()

        # D. Sub-k count (< 5 observations) must be suppressed
        sub_k_payload = {
            "features": [
                {
                    "properties": {"reported_cases": 2},  # < 5 threshold -> REJECT
                }
            ]
        }
        with pytest.raises(EgressGateViolation) as exc_k:
            check_k_anonymity_suppression("outbreak_aggregates", sub_k_payload)
        assert "k-anonymity" in str(exc_k.value).lower()

    def test_step_3_climate_analogue_matching(self):
        """Step 3: Bi-directional multivariate matching across India, Brazil, and South Africa."""
        matcher = ClimateAnalogueMatcher()
        # Maharashtra (IND) source
        src_maharashtra = SEEDED_BRICS_PROFILES[0]
        # Mato Grosso (BRA) candidate
        cand_mato_grosso = SEEDED_BRICS_PROFILES[1]

        # Compute similarity with hemispheric alignment
        result = matcher.compute_similarity(src_maharashtra, cand_mato_grosso)
        assert result.hemisphere_aligned is True
        assert "Mato Grosso" in result.analogue_region
        assert result.similarity_index > 0.60
        assert len(result.successful_regenerative_practices) > 0

    def test_step_4_model_hub_entry_signing_and_validation(self, temp_keys_dir):
        """Step 4: Create Model Hub entry, sign card metadata with Ed25519, and verify authenticity."""
        node_ind = NodeIdentity.load_or_create(temp_keys_dir, "node-ind-01", country_code="IND")

        card_dict = {
            "model_name": "MobileNetV3-BRICS-Disease",
            "version": "2.4.0",
            "author_node_id": node_ind.node_id,
            "quantization": "int8",
            "weights_sha256": "a4f89d38c20173e4b780df294bb89e623c0f49c0d127ef8c0a370e7a884e62a1",
        }
        canonical_card_bytes = json.dumps(card_dict, sort_keys=True).encode("utf-8")
        signature_b64 = node_ind.sign(canonical_card_bytes)

        # Verification using NodeIdentity
        assert node_ind.verify_signature(canonical_card_bytes, signature_b64) is True

        # Tampered card bytes must fail verification
        tampered_bytes = json.dumps({**card_dict, "version": "3.0.0"}, sort_keys=True).encode("utf-8")
        assert node_ind.verify_signature(tampered_bytes, signature_b64) is False

    @pytest.mark.asyncio
    async def test_step_5_flower_federated_learning_simulation(self, db_session):
        """Step 5: Run multi-round decentralized Flower simulation with DP noise and Byzantine filtering."""
        sim = FederatedSimulator(feature_dim=8, model_name="KrishiNet-BRICS-YieldPredictor")

        report = await sim.run_simulation(
            db=db_session,
            num_rounds=3,
            target_accuracy=0.70,
        )
        assert report.rounds_executed == 3
        assert report.zero_raw_data_transferred is True
        assert len(report.participating_nodes) == 3
        assert "node-ind-01" in report.participating_nodes
        assert report.total_epsilon_consumed <= 2.0
        assert len(report.round_history) == 3

    def test_step_6_kantara_consent_receipts_and_ledger(self, temp_keys_dir, temp_ledger_file):
        """Step 6 & 7: Append-only hash chain recording consent and cryptographic verification."""
        node_ind = NodeIdentity.load_or_create(temp_keys_dir, "node-ind-01", country_code="IND")
        ledger = ConsentLedger(storage_path=temp_ledger_file)
        manager = ConsentManager(identity=node_ind, country_iso="IN", node_id="node-ind-01")

        # A. Generate Kantara-compliant receipt
        user_id = "farmer-anon-001"
        scopes = {
            "share_anonymized_soil": True,
            "share_outbreak_telemetry": True,
            "participate_in_federated_learning": True,
        }
        receipt = manager.generate_receipt(user_id, scopes)
        assert receipt.version == "1.1.0"
        assert receipt.jurisdiction == "IN"
        assert receipt.signature is not None
        assert len(receipt.signature) > 0

        # B. Append blocks to ledger
        b0 = ledger.append_block(
            user_id=user_id,
            action="GRANT",
            scopes=scopes,
            receipt_id=receipt.receipt_id,
        )
        assert b0.block_index == 0
        assert b0.prev_hash == ConsentLedger.GENESIS_HASH

        b1 = ledger.append_block(
            user_id="farmer-anon-002",
            action="UPDATE",
            scopes={"share_soil": True},
            receipt_id="rec-002",
        )
        assert b1.block_index == 1
        assert b1.prev_hash == b0.block_hash

        # C. Verify unbroken hash chain
        is_valid, err = ledger.verify_chain()
        assert is_valid is True, f"Chain integrity failed: {err}"

    def test_step_8_fraud_and_tamper_detection(self, temp_ledger_file):
        """Step 8: Ensure hash chain detects retroactive block tampering."""
        ledger = ConsentLedger(storage_path=temp_ledger_file)

        # Create two blocks
        ledger.append_block("farmer-001", "GRANT", {"soil": True}, "rec-001")
        ledger.append_block("farmer-002", "GRANT", {"soil": True}, "rec-002")
        assert len(ledger.chain) == 2

        # Malicious actor tampers with block 0 payload
        ledger.chain[0].scopes = {"soil": False, "hacked": True}

        # Integrity verification must catch the fraud
        is_valid, err_msg = ledger.verify_chain()
        assert is_valid is False
        assert "corruption" in err_msg.lower() or "broken" in err_msg.lower()

"""
KrishiNet-BRICS - Node Federation Unit Tests (Part 7A).
Tests NodeIdentity, keypair generation, PEM serialization, and signed request headers.
"""

import base64
import hashlib
import json
import pytest
from pathlib import Path
from app.federation.identity import NodeIdentity


def test_node_identity_generation_and_headers():
    """Validates Ed25519 node keypair generation and signed request header assembly."""
    identity = NodeIdentity.generate(node_id="node-ind-test-01")
    assert identity.node_id == "node-ind-test-01"
    
    pub_b64 = identity.public_key_b64
    assert len(base64.b64decode(pub_b64)) == 32

    # Create signed request headers
    payload = {"status": "healthy", "crop": "cotton"}
    body_bytes = json.dumps(payload).encode("utf-8")
    headers = identity.create_signed_headers(body_bytes)

    assert headers["X-Node-ID"] == "node-ind-test-01"
    assert "X-Signature-Timestamp" in headers
    assert "X-Signature-Nonce" in headers
    assert "X-Signature-Ed25519" in headers

    # Verify signature using the public key
    from cryptography.hazmat.primitives.asymmetric import ed25519
    raw_pub = base64.b64decode(pub_b64)
    raw_sig = base64.b64decode(headers["X-Signature-Ed25519"])
    pub_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)

    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical_message = f"{headers['X-Node-ID']}:{headers['X-Signature-Timestamp']}:{headers['X-Signature-Nonce']}:{body_hash}".encode("utf-8")
    pub_key.verify(raw_sig, canonical_message)  # Passes without raising InvalidSignature


def test_node_identity_load_or_create(tmp_path: Path):
    """Ensures NodeIdentity idempotently saves and loads PEM keys from disk."""
    keys_dir = tmp_path / "keys"
    
    # 1. First run creates keys
    id1 = NodeIdentity.load_or_create(keys_dir, "node-test-02")
    pub1 = id1.public_key_b64
    assert (keys_dir / "ed25519_private.pem").exists()
    assert (keys_dir / "ed25519_public.pem").exists()

    # 2. Second run loads existing keys without regenerating
    id2 = NodeIdentity.load_or_create(keys_dir, "node-test-02")
    pub2 = id2.public_key_b64
    assert pub1 == pub2

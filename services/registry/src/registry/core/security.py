"""
BRICS Commons Registry - Cryptographic Security & Ed25519 Signature Verification.
Enforces non-repudiation, replay attack prevention, and sovereign node authentication.
"""

import base64
import hashlib
import time
from typing import Dict, Optional, Set, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from fastapi import Header, HTTPException, Request, status
from registry.core.config import settings

# In-memory nonce cache with timestamp for replay protection
_NONCE_CACHE: Dict[str, float] = {}


def _cleanup_old_nonces(now: float) -> None:
    """Removes nonces older than TTL to prevent memory unbounded growth."""
    cutoff = now - settings.NONCE_CACHE_TTL_SECONDS
    keys_to_remove = [k for k, ts in _NONCE_CACHE.items() if ts < cutoff]
    for k in keys_to_remove:
        _NONCE_CACHE.pop(k, None)


def verify_ed25519_signature(
    public_key_b64: str,
    signature_b64: str,
    message_bytes: bytes
) -> bool:
    """
    Verifies an Ed25519 signature over message bytes using a base64 encoded 32-byte public key.
    """
    try:
        raw_pub = base64.b64decode(public_key_b64)
        raw_sig = base64.b64decode(signature_b64)
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)
        pub_key.verify(raw_sig, message_bytes)
        return True
    except (ValueError, InvalidSignature, Exception):
        return False


def verify_replay_and_extract_payload(
    node_id: str,
    timestamp_str: str,
    nonce: str,
    signature_b64: str,
    body_bytes: bytes,
    public_key_b64: str,
) -> None:
    """
    Guarantees:
    1. Timestamp is within [-300s, +300s] of registry clock.
    2. Nonce has not been seen within the TTL window.
    3. Ed25519 signature of f"{node_id}:{timestamp_str}:{nonce}:{sha256(body)}" is cryptographically valid.
    """
    now = time.time()
    _cleanup_old_nonces(now)

    # 1. Timestamp validation
    try:
        ts = float(timestamp_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Signature-Timestamp header format."
        )

    if abs(now - ts) > settings.SIGNATURE_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Signature expired or timestamp drift exceeds {settings.SIGNATURE_MAX_AGE_SECONDS}s."
        )

    # 2. Nonce uniqueness check (replay protection)
    nonce_key = f"{node_id}:{nonce}"
    if nonce_key in _NONCE_CACHE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Replay attack detected: Nonce has already been processed."
        )
    _NONCE_CACHE[nonce_key] = now

    # 3. Message canonicalization and signature verification
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical_message = f"{node_id}:{timestamp_str}:{nonce}:{body_hash}".encode("utf-8")

    is_valid = verify_ed25519_signature(public_key_b64, signature_b64, canonical_message)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cryptographic Ed25519 signature verification failed."
        )


def verify_registry_admin(
    x_registry_admin_key: Optional[str] = Header(None, alias="X-Registry-Admin-Key")
) -> bool:
    """
    Enforces registry administrative role for node approvals and suspensions.
    Supports development auto-bypass or explicit admin API key.
    """
    if settings.ENVIRONMENT in ["dev", "development", "test", "testing"]:
        if not x_registry_admin_key or x_registry_admin_key == settings.REGISTRY_ADMIN_API_KEY:
            return True

    if x_registry_admin_key == settings.REGISTRY_ADMIN_API_KEY:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient privileges: Registry administrator authorization required."
    )

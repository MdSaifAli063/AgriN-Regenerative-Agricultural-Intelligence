"""
KrishiNet-BRICS - Node Federation Identity & Cryptographic Signatures.
Manages sovereign Ed25519 node keypairs and generates replay-protected signed request headers.
"""

import base64
import hashlib
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class NodeIdentity:
    """
    Sovereign Node Identity holding Ed25519 signing credentials.
    """

    def __init__(
        self,
        private_key: ed25519.Ed25519PrivateKey,
        node_id: str,
        country_code: Optional[str] = None,
    ):
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.node_id = node_id
        self.country_code = country_code or os.environ.get("LOCAL_NODE_COUNTRY_ISO", "IND")

    @property
    def public_key_b64(self) -> str:
        """Returns 32-byte public key encoded as Base64."""
        raw_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw_bytes).decode("utf-8")

    @property
    def public_key_hex(self) -> str:
        """Returns 32-byte public key encoded as Hex."""
        raw_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw_bytes.hex()

    def sign_message(self, message_bytes: bytes) -> str:
        """Signs raw message bytes and returns Base64 signature."""
        sig_bytes = self.private_key.sign(message_bytes)
        return base64.b64encode(sig_bytes).decode("utf-8")

    def sign(self, message_bytes: bytes) -> str:
        """Alias for sign_message."""
        return self.sign_message(message_bytes)

    def verify_signature(self, message_bytes: bytes, signature: Any) -> bool:
        """Verifies signature against this identity's public key (accepts Base64, hex, or raw bytes)."""
        try:
            if isinstance(signature, str):
                try:
                    sig_bytes = base64.b64decode(signature)
                except Exception:
                    sig_bytes = bytes.fromhex(signature)
            else:
                sig_bytes = signature
            self.public_key.verify(sig_bytes, message_bytes)
            return True
        except Exception:
            return False

    def create_signed_headers(self, body_bytes: bytes) -> Dict[str, str]:
        """
        Generates canonical replay-protected HTTP signature headers:
        X-Node-ID
        X-Signature-Timestamp
        X-Signature-Nonce
        X-Signature-Ed25519: sign(f"{node_id}:{timestamp}:{nonce}:{sha256(body)}")
        """
        timestamp_str = str(time.time())
        nonce = str(uuid.uuid4())
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        canonical_message = f"{self.node_id}:{timestamp_str}:{nonce}:{body_hash}".encode("utf-8")
        signature_b64 = self.sign_message(canonical_message)

        return {
            "X-Node-ID": self.node_id,
            "X-Signature-Timestamp": timestamp_str,
            "X-Signature-Nonce": nonce,
            "X-Signature-Ed25519": signature_b64,
        }

    @classmethod
    def generate(cls, node_id: str, country_code: Optional[str] = None) -> "NodeIdentity":
        """Generates a fresh in-memory Ed25519 keypair."""
        priv = ed25519.Ed25519PrivateKey.generate()
        return cls(priv, node_id, country_code=country_code)

    @classmethod
    def load_or_create(
        cls,
        arg1: Union[Path, str],
        arg2: Union[Path, str],
        arg3: Optional[Union[Path, str]] = None,
        country_code: Optional[str] = None,
    ) -> "NodeIdentity":
        """
        Loads existing private key from disk or generates and saves a new one.
        Handles flexible parameter order: (keys_dir, node_id) or (node_id, country_code, keys_dir).
        """
        if isinstance(arg1, Path):
            keys_dir = arg1
            node_id = str(arg2)
            c_code = str(arg3) if isinstance(arg3, str) else country_code
        elif isinstance(arg2, Path):
            node_id = str(arg1)
            keys_dir = arg2
            c_code = str(arg3) if isinstance(arg3, str) else country_code
        elif isinstance(arg3, Path):
            node_id = str(arg1)
            c_code = str(arg2)
            keys_dir = arg3
        else:
            keys_dir = Path(str(arg1))
            node_id = str(arg2)
            c_code = country_code

        keys_dir.mkdir(parents=True, exist_ok=True)
        priv_path = keys_dir / f"ed25519_private_{node_id}.pem"
        pub_path = keys_dir / f"ed25519_public_{node_id}.pem"

        # Also fallback to standard filename if node-specific doesn't exist
        fallback_priv = keys_dir / "ed25519_private.pem"
        fallback_pub = keys_dir / "ed25519_public.pem"

        if priv_path.exists():
            target_priv = priv_path
        elif fallback_priv.exists() and not any(keys_dir.glob("ed25519_private_*.pem")):
            target_priv = fallback_priv
        else:
            target_priv = priv_path

        if target_priv.exists():
            with open(target_priv, "rb") as f:
                priv = serialization.load_pem_private_key(f.read(), password=None)
                if not isinstance(priv, ed25519.Ed25519PrivateKey):
                    raise ValueError(f"Key in {target_priv} is not an Ed25519 private key.")
                return cls(priv, node_id, country_code=c_code)

        # Generate new key
        priv = ed25519.Ed25519PrivateKey.generate()
        pem_bytes = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        with open(priv_path, "wb") as f:
            f.write(pem_bytes)

        pub_bytes = priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with open(pub_path, "wb") as f:
            f.write(pub_bytes)

        # Also write generic pem filenames for backwards compatibility
        if not fallback_priv.exists():
            with open(fallback_priv, "wb") as f:
                f.write(pem_bytes)
        if not fallback_pub.exists():
            with open(fallback_pub, "wb") as f:
                f.write(pub_bytes)

        return cls(priv, node_id, country_code=c_code)


def get_node_identity(keys_dir: Optional[Path] = None, node_id: Optional[str] = None) -> NodeIdentity:
    """Helper to retrieve or initialize the local sovereign node identity."""
    dir_path = keys_dir or Path(os.environ.get("NODE_KEY_DIR", ".node_keys"))
    nid = node_id or os.environ.get("NODE_ID", "node-ind-icar-01")
    c_code = os.environ.get("LOCAL_NODE_COUNTRY_ISO", "IND")
    return NodeIdentity.load_or_create(dir_path, nid, country_code=c_code)


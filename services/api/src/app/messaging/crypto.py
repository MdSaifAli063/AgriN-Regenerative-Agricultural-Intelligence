"""
Cryptographic and Data Minimisation Utilities for Messaging Gateway.
Implements:
1. Salted SHA-256 phone number hashing for O(1) indexed lookups without exposing PII.
2. Fernet symmetric encryption for storing recoverable phone numbers for replies.
3. Phone number normalization (E.164 standard).
"""

import hashlib
import re
from typing import Optional
from cryptography.fernet import Fernet
import phonenumbers
from app.core.config import settings


def normalize_phone_number(raw_phone: str, default_region: str = "IN") -> str:
    """
    Normalizes any input phone number into strict E.164 format (+[country_code][number]).
    Handles prefixes like 'whatsapp:+91...' cleanly.
    """
    cleaned = raw_phone.strip()
    if cleaned.lower().startswith("whatsapp:"):
        cleaned = cleaned[9:].strip()

    try:
        parsed = phonenumbers.parse(cleaned, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass

    # Fallback cleanup: keep digits and leading '+'
    digits_only = re.sub(r"[^\d+]", "", cleaned)
    if not digits_only.startswith("+"):
        # Assume country code if not present (defaulting to +91 or +55 or +27 by node)
        country_prefix_map = {"IND": "+91", "BRA": "+55", "ZAF": "+27", "RUS": "+7", "CHN": "+86"}
        prefix = country_prefix_map.get(settings.NODE_COUNTRY, "+91")
        digits_only = f"{prefix}{digits_only.lstrip('0')}"
    return digits_only


def hash_phone_number(phone: str, salt: Optional[str] = None) -> str:
    """
    Computes deterministic salted SHA-256 hash of normalized phone number.
    Safe for database indexing, search, and privacy preservation.
    """
    norm = normalize_phone_number(phone)
    active_salt = salt or settings.MESSAGING_PHONE_SALT
    combined = f"{active_salt}:{norm}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def _get_fernet() -> Fernet:
    """Initializes Fernet cipher using configured or deterministically derived 32-byte key."""
    raw = settings.MESSAGING_ENCRYPTION_KEY
    try:
        return Fernet(raw.encode("utf-8"))
    except Exception:
        import base64
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
        return Fernet(derived)


def encrypt_phone_number(phone: str) -> str:
    """
    Encrypts normalized phone number into a Fernet ciphertext token.
    Stored only when outbound message reply capability is necessary.
    """
    norm = normalize_phone_number(phone)
    fernet = _get_fernet()
    return fernet.encrypt(norm.encode("utf-8")).decode("utf-8")


def decrypt_phone_number(token: str) -> str:
    """
    Decrypts Fernet ciphertext token back into plain E.164 phone number.
    """
    fernet = _get_fernet()
    return fernet.decrypt(token.encode("utf-8")).decode("utf-8")

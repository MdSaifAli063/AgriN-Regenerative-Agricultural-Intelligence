"""
BRICS Commons Registry - SQL Database Models for Nodes, Keys, and Sovereign Audit Log.
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from registry.db.session import Base


class RegistryNode(Base):
    """
    Sovereign Node Record registered with the BRICS Commons.
    Contains zero farmer PII and only high-level institution and endpoint metadata.
    """
    __tablename__ = "registry_nodes"

    id = Column(String(64), primary_key=True, index=True)  # e.g., "node-ind-icar-01"
    country_code = Column(String(8), nullable=False, index=True)  # e.g., "IND" or "IN"
    organisation_name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending, approved, suspended, revoked
    api_base_url = Column(String(512), nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)  # ["stac", "jsonld", "flower_fl", "outbreak_feed"]
    version = Column(String(32), nullable=False, default="1.0.0")
    contact_email = Column(String(255), nullable=False)
    
    registered_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    is_stale = Column(Boolean, default=False, nullable=False)

    # Coarsened, aggregated national statistics (non-PII)
    metrics_summary = Column(JSON, nullable=False, default=dict)

    # Relationships
    keys = relationship("RegistryNodeKey", back_populates="node", cascade="all, delete-orphan")


class RegistryNodeKey(Base):
    """
    Cryptographic Ed25519 Public Keys associated with a sovereign node.
    Supports key rotation with an active grace period overlap window.
    """
    __tablename__ = "registry_node_keys"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id = Column(String(64), ForeignKey("registry_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    public_key = Column(Text, nullable=False)  # Base64 encoded 32-byte Ed25519 public key
    key_version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active")  # active, grace_period, archived, revoked
    
    valid_from = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    node = relationship("RegistryNode", back_populates="keys")


class RegistryAuditLog(Base):
    """
    Immutable Cryptographic Audit Trail for all Registry operations.
    Logs payload hashes, actor node identities, and security state changes.
    """
    __tablename__ = "registry_audit_logs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(64), nullable=False, index=True)  # node_id or "registry-admin"
    action = Column(String(64), nullable=False, index=True)   # node_register, node_approve, key_rotate, etc.
    target_id = Column(String(64), nullable=False, index=True)
    payload_hash = Column(String(64), nullable=False)  # SHA-256 hex digest
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    details = Column(JSON, nullable=True)

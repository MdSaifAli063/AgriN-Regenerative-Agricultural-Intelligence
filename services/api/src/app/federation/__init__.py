"""
KrishiNet-BRICS - Node Federation Module.
"""

from app.federation.identity import NodeIdentity
from app.federation.heartbeat import dispatch_node_heartbeat

__all__ = ["NodeIdentity", "dispatch_node_heartbeat"]

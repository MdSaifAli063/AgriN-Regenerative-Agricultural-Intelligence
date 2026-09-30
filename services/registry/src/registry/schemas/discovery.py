"""
BRICS Commons Registry - Discovery Document Schema.
Complies with /.well-known/agrin-registry.json standard.
"""

from typing import List, Dict
from pydantic import BaseModel, ConfigDict


class DiscoveryDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agrin_version: str
    registry_id: str
    federation_standard: str
    supported_protocols: List[str]
    endpoints: Dict[str, str]
    signature_algorithm: str
    privacy_guarantees: List[str]
    participating_nations: List[str]

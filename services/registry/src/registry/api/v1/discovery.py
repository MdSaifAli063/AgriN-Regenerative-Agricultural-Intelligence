"""
BRICS Commons Registry - Well-Known Discovery Document Endpoint.
Serves /.well-known/agrin-registry.json for automated country node bootstrap and protocol discovery.
"""

from fastapi import APIRouter
from registry.core.config import settings
from registry.schemas.discovery import DiscoveryDocumentResponse

router = APIRouter(tags=["Federation Protocol Discovery"])


@router.get(
    "/.well-known/agrin-registry.json",
    response_model=DiscoveryDocumentResponse,
    summary="BRICS Commons Registry discovery document",
)
async def get_discovery_document():
    return DiscoveryDocumentResponse(
        agrin_version="1.0.0",
        registry_id="brics-commons-registry-01",
        federation_standard="BRICS-AgriN-2026.1",
        supported_protocols=[
            "stac-1.0.0",
            "geojson-rfc7946",
            "json-ld-agrovoc",
            "flower-fl-grpc",
            "ed25519-http-signatures",
        ],
        endpoints={
            "nodes": f"{settings.API_V1_STR}/nodes",
            "heartbeat": f"{settings.API_V1_STR}/nodes/{{id}}/heartbeat",
            "models": f"{settings.API_V1_STR}/models",
            "analogues": f"{settings.API_V1_STR}/analogues",
            "agreements": f"{settings.API_V1_STR}/agreements",
            "health": "/health",
        },
        signature_algorithm="Ed25519",
        privacy_guarantees=[
            "extra_forbid_zero_pii",
            "coordinate_precision_max_2_decimals",
            "k_anonymity_5_suppression",
            "laplace_differential_privacy_epsilon_0.5",
            "byzantine_robust_trimmed_mean",
        ],
        participating_nations=["IND", "BRA", "ZAF", "CHN", "RUS", "ETH", "EGY", "IRN", "UAE"],
    )

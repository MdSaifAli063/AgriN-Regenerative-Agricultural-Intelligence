"""
KrishiNet-BRICS – Outbreak Feed Builder.

Produces two machine-readable representations of the outbreak aggregate data:

1. GeoJSON FeatureCollection
   - One Feature per OutbreakAggregate
   - Geometry: Point (centroid_lon, centroid_lat)
   - Properties: disease_name, affected_crop, incident_count, risk_severity,
     h3_hex_index, country_iso, period_start, period_end
   - Used by frontend map components and external GIS tools.

2. JSON-LD (schema.org/Event + FAO AGROVOC extension)
   - Wraps each aggregate as a schema:Event with geo:SpatialThing
   - Includes @context with AGROVOC and WGS84 vocabulary links
   - Enables semantic web interoperability with FAO/CGIAR data portals.

Both formats are generated in-memory (no DB access needed) from
List[OutbreakAggregate] passed by the API router.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.disease import OutbreakAggregate


# ---------------------------------------------------------------------------
# GeoJSON builder
# ---------------------------------------------------------------------------

def build_geojson_feed(
    aggregates: List[OutbreakAggregate],
    generated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Constructs a GeoJSON FeatureCollection from a list of OutbreakAggregate
    objects.

    Args:
        aggregates:    Outbreak aggregate records from the DB.
        generated_at:  Timestamp to embed in metadata (defaults to now).

    Returns:
        Python dict conforming to GeoJSON FeatureCollection spec (RFC 7946).
    """
    if generated_at is None:
        from datetime import timezone
        generated_at = datetime.now(timezone.utc)

    features = []
    for agg in aggregates:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [agg.centroid_lon, agg.centroid_lat],  # [lon, lat] per GeoJSON spec
            },
            "properties": {
                "id": agg.id,
                "disease_name": agg.disease_name,
                "affected_crop": agg.affected_crop,
                "incident_count": agg.incident_count,
                "risk_severity": agg.risk_severity,
                "h3_hex_index": agg.h3_hex_index,
                "country_iso": agg.country_iso,
                "period_start": _iso(agg.period_start),
                "period_end": _iso(agg.period_end),
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "generated_at": _iso(generated_at),
            "total_features": len(features),
            "data_standard": "GeoJSON RFC 7946",
            "privacy_notice": (
                "All locations are coarsened to H3 resolution-6 (~36 km²). "
                "Incident counts include Laplace differential privacy noise (ε=1.0). "
                "Only farmers who granted outbreak telemetry consent are included."
            ),
        },
    }


# ---------------------------------------------------------------------------
# JSON-LD builder
# ---------------------------------------------------------------------------

_JSONLD_CONTEXT = {
    "@vocab": "https://schema.org/",
    "agrovoc": "http://aims.fao.org/aos/agrovoc/",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "h3": "https://h3geo.org/docs/core-library/restable/#table-of-contents",
    "krishinet": "https://krishinet-brics.org/ontology/v1#",
    "disease_name": "krishinet:diseaseName",
    "affected_crop": "agrovoc:c_1972",
    "incident_count": "krishinet:incidentCount",
    "risk_severity": "krishinet:riskSeverity",
    "h3_hex_index": "h3:hexIndex",
    "country_iso": "krishinet:countryISO",
    "period_start": "schema:startDate",
    "period_end": "schema:endDate",
}


def build_jsonld_feed(
    aggregates: List[OutbreakAggregate],
    generated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Constructs a JSON-LD @graph from a list of OutbreakAggregate objects.

    Each aggregate becomes a schema:Event describing a disease outbreak cluster.

    Args:
        aggregates:   Outbreak aggregate records.
        generated_at: Timestamp for metadata.

    Returns:
        Python dict conforming to JSON-LD 1.1 spec.
    """
    if generated_at is None:
        from datetime import timezone
        generated_at = datetime.now(timezone.utc)

    graph = []
    for agg in aggregates:
        node = {
            "@type": "Event",
            "@id": f"urn:krishinet:outbreak:{agg.id}",
            "name": f"{agg.disease_name} outbreak – {agg.country_iso}",
            "description": (
                f"Aggregated {agg.disease_name} detections in {agg.country_iso} "
                f"affecting {agg.affected_crop} crops. "
                f"Incident count: ~{agg.incident_count} (privacy-noised). "
                f"Risk level: {agg.risk_severity}."
            ),
            "disease_name": agg.disease_name,
            "affected_crop": agg.affected_crop,
            "incident_count": agg.incident_count,
            "risk_severity": agg.risk_severity,
            "h3_hex_index": agg.h3_hex_index,
            "country_iso": agg.country_iso,
            "period_start": _iso(agg.period_start),
            "period_end": _iso(agg.period_end),
            "location": {
                "@type": "Place",
                "geo": {
                    "@type": "GeoCoordinates",
                    "geo:lat": agg.centroid_lat,
                    "geo:long": agg.centroid_lon,
                },
            },
        }
        graph.append(node)

    return {
        "@context": _JSONLD_CONTEXT,
        "@type": "Dataset",
        "@id": "urn:krishinet:outbreak-feed",
        "name": "KrishiNet-BRICS Outbreak Intelligence Feed",
        "description": (
            "Privacy-preserving crop disease outbreak aggregates from sovereign "
            "BRICS nodes. Locations are H3 resolution-6 geo-coarsened; "
            "counts include Laplace differential privacy noise."
        ),
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {
            "@type": "Organization",
            "name": "KrishiNet-BRICS Consortium",
            "url": "https://krishinet-brics.org",
        },
        "dateModified": _iso(generated_at),
        "@graph": graph,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

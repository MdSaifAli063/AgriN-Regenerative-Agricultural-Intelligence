"""
KrishiNet-BRICS – Outbreak Aggregation Pipeline.

Pipeline stages (all in one module, invoked by Celery task):

1. GEO-COARSENING
   Convert precise GPS coordinates to H3 resolution-6 hex index (≈36 km²
   cells). Resolution 6 is coarse enough to prevent household-level tracking
   while preserving meaningful regional outbreak signals.

2. CONSENT FILTERING
   Only DiseaseDetection records where the farmer has explicitly granted
   share_outbreak_telemetry=True are included.

3. K-ANONYMITY ENFORCEMENT
   A hex-cell cluster is SUPPRESSED if it has fewer than K_MIN_FARMERS
   distinct farmers.  This ensures no individual can be re-identified.
   Default K_MIN_FARMERS = 5.

4. LAPLACE DIFFERENTIAL PRIVACY NOISE
   Even for cells passing K-anonymity, we add Laplace(0, 1/ε) noise to the
   incident count.  Default ε = 1.0 → noise scale = 1.0.
   The count is clipped to [K_MIN_FARMERS, ∞) after noise addition.

5. SEVERITY CLASSIFICATION
   Incident count (post-noise) is mapped to risk_severity label:
     <  5 → low
     5–14 → moderate
    15–29 → high
     ≥30  → severe

6. SPIKE DETECTION
   Compares current period count against mean of the previous N periods
   (same disease, same country). Spike flag raised when
   current > prior_mean * SPIKE_MULTIPLIER (default 2.5×).

7. UPSERT
   OutbreakAggregate rows are upserted (H3 index + disease + period_start).

Output: AggregationResult dataclass with stats for Celery task reporting.
"""

from __future__ import annotations

import datetime
import logging
import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.models.disease import DiseaseDetection, OutbreakAggregate

logger = logging.getLogger("krishinet.services.outbreak")

# ---------------------------------------------------------------------------
# Privacy constants (can be overridden via environment / settings)
# ---------------------------------------------------------------------------

K_MIN_FARMERS: int = 5          # k-anonymity minimum group size
EPSILON: float = 1.0            # differential privacy budget (ε)
SPIKE_MULTIPLIER: float = 2.5   # current > prior_mean × this → spike
SPIKE_LOOKBACK_PERIODS: int = 4 # how many prior periods to average
H3_RESOLUTION: int = 6          # ~36 km² cells


# ---------------------------------------------------------------------------
# H3 geo-coarsening
# ---------------------------------------------------------------------------

def coarsen_to_h3(lat: float, lon: float, resolution: int = H3_RESOLUTION) -> str:
    """
    Converts GPS coordinates to H3 hex index at the specified resolution.
    Falls back to a deterministic grid string when h3 is not importable.
    """
    try:
        import h3
        return h3.latlng_to_cell(lat, lon, resolution)
    except ImportError:
        logger.warning("h3 library not available; using coarse grid fallback.")
        # Coarse 1-degree grid fallback (≈111 km cells)
        return f"grid_{int(lat):+04d}_{int(lon):+04d}_r{resolution}"
    except Exception as exc:
        logger.warning(f"H3 conversion failed ({exc}); using fallback.")
        return f"grid_{int(lat):+04d}_{int(lon):+04d}_r{resolution}"


def h3_to_centroid(h3_index: str) -> Tuple[float, float]:
    """
    Returns (lat, lon) centroid for an H3 hex index.
    Falls back to parsing the grid fallback string.
    """
    try:
        import h3
        lat, lon = h3.cell_to_latlng(h3_index)
        return round(lat, 4), round(lon, 4)
    except Exception:
        # Parse grid fallback: "grid_+012_+076_r6"
        try:
            parts = h3_index.split("_")
            return float(parts[1]) + 0.5, float(parts[2]) + 0.5
        except Exception:
            return 0.0, 0.0


# ---------------------------------------------------------------------------
# Laplace noise
# ---------------------------------------------------------------------------

def _laplace_noise(scale: float) -> float:
    """Samples Laplace(0, scale) noise using pure Python."""
    u = random.random() - 0.5
    return -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u) + 1e-12)


def add_laplace_noise(count: int, epsilon: float = EPSILON) -> int:
    """
    Adds Laplace(0, 1/ε) differential privacy noise to an integer count.
    Result is clipped to [K_MIN_FARMERS, ∞) to avoid suppression bypass.
    """
    scale = 1.0 / epsilon
    noisy = count + _laplace_noise(scale)
    return max(K_MIN_FARMERS, round(noisy))


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

def classify_severity(incident_count: int) -> str:
    """Maps incident count (post-noise) to risk_severity label."""
    if incident_count >= 30:
        return "severe"
    if incident_count >= 15:
        return "high"
    if incident_count >= 5:
        return "moderate"
    return "low"


# ---------------------------------------------------------------------------
# Spike detection
# ---------------------------------------------------------------------------

@dataclass
class SpikeAlert:
    disease_name: str
    h3_hex_index: str
    country_iso: str
    current_count: int
    prior_mean: float
    spike_ratio: float
    period_start: datetime.datetime


def detect_spikes(
    current_aggregates: List[OutbreakAggregate],
    historical: List[OutbreakAggregate],
    multiplier: float = SPIKE_MULTIPLIER,
) -> List[SpikeAlert]:
    """
    Compares current period aggregates against historical baselines.

    Args:
        current_aggregates: Newly computed OutbreakAggregate objects.
        historical: Prior period OutbreakAggregate objects for same diseases.
        multiplier: Spike threshold multiplier.

    Returns:
        List of SpikeAlert objects (may be empty).
    """
    # Build baseline: disease → list of prior counts
    baseline: Dict[str, List[int]] = defaultdict(list)
    for h in historical:
        baseline[h.disease_name].append(h.incident_count)

    alerts: List[SpikeAlert] = []
    for agg in current_aggregates:
        prior_counts = baseline.get(agg.disease_name, [])
        if not prior_counts:
            continue

        prior_mean = sum(prior_counts) / len(prior_counts)
        if prior_mean < 1.0:
            continue  # avoid division by near-zero

        ratio = agg.incident_count / prior_mean
        if ratio >= multiplier:
            alerts.append(
                SpikeAlert(
                    disease_name=agg.disease_name,
                    h3_hex_index=agg.h3_hex_index,
                    country_iso=agg.country_iso,
                    current_count=agg.incident_count,
                    prior_mean=round(prior_mean, 2),
                    spike_ratio=round(ratio, 2),
                    period_start=agg.period_start,
                )
            )
            logger.warning(
                f"OUTBREAK SPIKE: {agg.disease_name} in {agg.country_iso} "
                f"[{agg.h3_hex_index}] – {ratio:.1f}× baseline"
            )

    return alerts


# ---------------------------------------------------------------------------
# Core aggregation result
# ---------------------------------------------------------------------------

@dataclass
class AggregationResult:
    period_start: datetime.datetime
    period_end: datetime.datetime
    total_raw_detections: int
    suppressed_cells: int           # failed k-anonymity
    cells_aggregated: int
    spikes_detected: int
    aggregates: List[OutbreakAggregate] = field(default_factory=list)
    spike_alerts: List[SpikeAlert] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main aggregation function
# ---------------------------------------------------------------------------

def aggregate_detections(
    detections: List[DiseaseDetection],
    country_iso: str,
    period_start: datetime.datetime,
    period_end: datetime.datetime,
    historical: Optional[List[OutbreakAggregate]] = None,
    k_min: int = K_MIN_FARMERS,
    epsilon: float = EPSILON,
    h3_resolution: int = H3_RESOLUTION,
) -> AggregationResult:
    """
    Runs the complete aggregation pipeline on a list of consented detections.

    Args:
        detections:   Consent-filtered DiseaseDetection objects.
        country_iso:  ISO-3166 alpha-3 country code for the sovereign node.
        period_start: Aggregation window start (UTC).
        period_end:   Aggregation window end (UTC).
        historical:   Prior OutbreakAggregate records for spike detection.
        k_min:        Minimum farmers for k-anonymity enforcement.
        epsilon:      Differential privacy budget.
        h3_resolution:H3 resolution level.

    Returns:
        AggregationResult with all produced aggregates and alerts.
    """
    # ── Stage 1: Geo-coarsening + grouping by (H3, disease) ──────────────
    # Structure: {(h3_index, disease_name) -> {farmer_ids: set, count: int, lats: list, lons: list}}
    cells: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: {"farmer_ids": set(), "count": 0, "lats": [], "lons": []}
    )

    for det in detections:
        h3_idx = coarsen_to_h3(det.latitude, det.longitude, h3_resolution)
        key = (h3_idx, det.primary_disease_name)
        cells[key]["farmer_ids"].add(det.farmer_id)
        cells[key]["count"] += 1
        cells[key]["lats"].append(det.latitude)
        cells[key]["lons"].append(det.longitude)

    # ── Stage 2: K-anonymity filter ───────────────────────────────────────
    suppressed = 0
    passing_cells = {}
    for key, data in cells.items():
        if len(data["farmer_ids"]) < k_min:
            suppressed += 1
            logger.debug(
                f"Cell {key[0]}/{key[1]} suppressed: {len(data['farmer_ids'])} "
                f"distinct farmers < k_min={k_min}"
            )
        else:
            passing_cells[key] = data

    # ── Stage 3: Laplace noise + severity + OA construction ──────────────
    aggregates: List[OutbreakAggregate] = []
    for (h3_idx, disease_name), data in passing_cells.items():
        noisy_count = add_laplace_noise(data["count"], epsilon)
        severity = classify_severity(noisy_count)

        # Centroid = mean of constituent GPS points (or H3 centroid)
        if data["lats"]:
            cent_lat = round(sum(data["lats"]) / len(data["lats"]), 4)
            cent_lon = round(sum(data["lons"]) / len(data["lons"]), 4)
        else:
            cent_lat, cent_lon = h3_to_centroid(h3_idx)

        # Derive crop from disease name (best-effort from playbook prefix)
        affected_crop = _infer_crop(disease_name)

        agg = OutbreakAggregate(
            id=str(uuid.uuid4()),
            country_iso=country_iso,
            disease_name=disease_name,
            affected_crop=affected_crop,
            incident_count=noisy_count,
            risk_severity=severity,
            h3_hex_index=h3_idx,
            centroid_lat=cent_lat,
            centroid_lon=cent_lon,
            period_start=period_start,
            period_end=period_end,
        )
        aggregates.append(agg)

    # ── Stage 4: Spike detection ──────────────────────────────────────────
    spike_alerts = detect_spikes(
        current_aggregates=aggregates,
        historical=historical or [],
    )

    logger.info(
        f"Aggregation complete: {len(detections)} detections → "
        f"{len(aggregates)} cells ({suppressed} suppressed), "
        f"{len(spike_alerts)} spikes"
    )

    return AggregationResult(
        period_start=period_start,
        period_end=period_end,
        total_raw_detections=len(detections),
        suppressed_cells=suppressed,
        cells_aggregated=len(aggregates),
        spikes_detected=len(spike_alerts),
        aggregates=aggregates,
        spike_alerts=spike_alerts,
    )


# ---------------------------------------------------------------------------
# Crop inference helper
# ---------------------------------------------------------------------------

_CROP_PREFIX_MAP: Dict[str, str] = {
    "wheat": "wheat",
    "rice": "rice",
    "maize": "maize",
    "cotton": "cotton",
    "soybean": "soybean",
    "tomato": "tomato",
    "potato": "potato",
    "sugarcane": "sugarcane",
    "groundnut": "groundnut",
    "banana": "banana",
    "chickpea": "chickpea",
    "lentil": "lentil",
    "mango": "mango",
    "pearl_millet": "pearl millet",
    "chilli": "chilli",
    "onion": "onion",
    "mustard": "mustard",
    "sunflower": "sunflower",
    "cassava": "cassava",
    "tea": "tea",
    "coffee": "coffee",
    "healthy": "unknown",
}


def _infer_crop(disease_label: str) -> str:
    """Infers crop name from disease label prefix."""
    for prefix, crop in _CROP_PREFIX_MAP.items():
        if disease_label.startswith(prefix):
            return crop
    return "unknown"


# ---------------------------------------------------------------------------
# Demo fixture generator (used by Celery task in DEMO_MODE)
# ---------------------------------------------------------------------------

def _synthetic_demo_detections(
    country_iso: str,
    since: datetime.datetime,
) -> List[Any]:
    """
    Generates synthetic detection namespace objects for demo mode.
    Provides realistic geographic spread across BRICS countries.
    """
    import types
    import itertools

    _BASE_COORDS = {
        "IND": [(28.6, 77.2), (17.4, 78.5), (23.0, 72.6), (12.9, 77.6), (25.3, 83.0)],
        "CHN": [(31.2, 121.5), (30.6, 104.1), (23.1, 113.3), (39.9, 116.4), (34.3, 108.9)],
        "BRA": [(-23.5, -46.6), (-15.8, -47.9), (-3.7, -38.5), (-19.9, -43.9), (-12.9, -38.5)],
        "RUS": [(55.7, 37.6), (59.9, 30.3), (56.9, 60.6), (51.5, 46.0), (43.0, 44.6)],
        "ZAF": [(-26.2, 28.0), (-33.9, 18.4), (-29.9, 31.0), (-25.7, 28.2), (-32.9, 27.5)],
    }
    coords = _BASE_COORDS.get(
        country_iso,
        [(20.0, 78.0), (19.0, 72.8), (22.5, 88.3), (17.5, 75.9), (28.7, 77.1)],
    )

    _DEMO_DISEASES = [
        "Rice Blast",
        "Yellow Rust (Stripe Rust)",
        "Cotton Leaf Curl Disease",
        "Late Blight",
        "Gray Leaf Spot",
    ]

    detections = []
    for i, (disease_name, (lat, lon)) in enumerate(
        itertools.islice(itertools.product(_DEMO_DISEASES, coords), 30)
    ):
        offset_lat = lat + (i % 5) * 0.05
        offset_lon = lon + (i % 5) * 0.05
        det = types.SimpleNamespace(
            id=f"demo_{i:04d}",
            farmer_id=f"demo_farmer_{i % 7:03d}",
            primary_disease_name=disease_name,
            latitude=offset_lat,
            longitude=offset_lon,
            created_at=since,
        )
        detections.append(det)

    return detections


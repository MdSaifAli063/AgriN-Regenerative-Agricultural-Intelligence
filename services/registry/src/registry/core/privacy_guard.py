"""
BRICS Commons Registry - Anti-Leak Privacy Guard.
Strictly ensures that no farmer PII, raw coordinates, cadastral polygons, or leaf images
can physically be received or stored by the Registry.
"""

from typing import Any, Dict, List, Set, Tuple
from fastapi import HTTPException, status
from registry.core.config import settings


class PrivacyViolationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "PRIVACY_GUARD_VIOLATION",
                "message": detail,
                "sovereignty_rule": "The BRICS Commons Registry enforces a strict zero-PII and coarse-spatial data policy."
            }
        )


def _count_decimal_places(val: float) -> int:
    """Returns number of decimal digits after decimal point."""
    str_val = f"{val:.10f}".rstrip("0")
    if "." not in str_val:
        return 0
    return len(str_val.split(".")[1])


def validate_no_pii_or_fine_coordinates(data: Any, path: str = "") -> None:
    """
    Recursively scans incoming request payloads:
    1. Rejects any key matching denied PII fields.
    2. Rejects any coordinate with more than MAX_COORDINATE_DECIMALS (default 2 decimals).
    3. Rejects base64-like image strings or raw binary representations.
    """
    denylist: Set[str] = set(settings.DENIED_PII_FIELDS)

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            lower_key = str(key).lower()

            # Check denylist (exact match or targeted privacy patterns)
            is_denied = (
                lower_key in denylist
                or lower_key in ["farmer", "cadastre", "polygon", "field_polygon", "leaf_img", "raw_image"]
                or "farmer_id" in lower_key
                or "farmer_name" in lower_key
                or "phone" in lower_key
                or "boundary" in lower_key
                or "cadastre" in lower_key
                or "polygon" in lower_key
            )
            if is_denied:
                raise PrivacyViolationError(
                    f"Denied PII / Sovereign private cadastre field '{current_path}' detected in payload."
                )

            # Check coordinate keys specifically
            if lower_key in ["lat", "latitude", "lon", "lng", "longitude", "coord", "coordinates"]:
                if isinstance(value, (int, float)):
                    decimals = _count_decimal_places(float(value))
                    if decimals > settings.MAX_COORDINATE_DECIMALS:
                        raise PrivacyViolationError(
                            f"Coordinate '{current_path}' has precision {decimals} decimals (> {settings.MAX_COORDINATE_DECIMALS}). "
                            "Registry only accepts coarse regional/H3 centroids with max 2 decimal places."
                        )
                elif isinstance(value, (list, tuple)):
                    for idx, coord_elem in enumerate(value):
                        if isinstance(coord_elem, (int, float)):
                            decimals = _count_decimal_places(float(coord_elem))
                            if decimals > settings.MAX_COORDINATE_DECIMALS:
                                raise PrivacyViolationError(
                                    f"Coordinate array '{current_path}[{idx}]' has precision {decimals} decimals "
                                    f"(> {settings.MAX_COORDINATE_DECIMALS}). Max 2 decimal places allowed."
                                )

            # Recurse
            validate_no_pii_or_fine_coordinates(value, current_path)

    elif isinstance(data, list):
        for idx, item in enumerate(data):
            current_path = f"{path}[{idx}]"
            validate_no_pii_or_fine_coordinates(item, current_path)

    elif isinstance(data, (int, float)):
        # Check if field name in path suggests coordinates
        last_field = path.split(".")[-1].split("[")[0].lower()
        if last_field in ["lat", "latitude", "lon", "lng", "longitude"]:
            decimals = _count_decimal_places(float(data))
            if decimals > settings.MAX_COORDINATE_DECIMALS:
                raise PrivacyViolationError(
                    f"Coordinate at '{path}' has precision {decimals} decimals (> {settings.MAX_COORDINATE_DECIMALS})."
                )

    elif isinstance(data, str):
        # Prevent base64 image data URI injection
        if data.startswith("data:image/") or (len(data) > 50000 and "==" in data[-4:]):
            raise PrivacyViolationError(
                f"Binary / Base64 image payload detected at '{path}'. Raw images are strictly prohibited in Registry."
            )

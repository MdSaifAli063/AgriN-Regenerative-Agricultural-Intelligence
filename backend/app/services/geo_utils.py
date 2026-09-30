import math
from typing import Any, Dict, List, Tuple
from shapely.geometry import shape, Polygon, Point


def calculate_polygon_metrics(geojson_geom: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Given a GeoJSON geometry (Polygon), calculate:
    1. Centroid Latitude
    2. Centroid Longitude
    3. Approximate Area in Hectares using an ellipsoidal authalic calculation.
    """
    geom = shape(geojson_geom)
    
    if isinstance(geom, Point):
        return geom.y, geom.x, 1.0  # 1 hectare default for point pin

    if not isinstance(geom, Polygon):
        raise ValueError(f"Geometry type {geom.geom_type} is not a Polygon or Point.")

    centroid = geom.centroid
    centroid_lat = float(centroid.y)
    centroid_lon = float(centroid.x)

    # Calculate area on WGS84 sphere/ellipsoid approximation
    # 1 deg latitude ~ 111,139 meters
    # 1 deg longitude ~ 111,139 * cos(lat) meters
    lat_rad = math.radians(centroid_lat)
    meters_per_deg_lat = 111139.0
    meters_per_deg_lon = 111139.0 * math.cos(lat_rad)

    coords = list(geom.exterior.coords)
    if len(coords) < 4:
        raise ValueError("Polygon must have at least 3 distinct vertices.")

    # Shoelace formula converted to square meters
    area_sq_m = 0.0
    for i in range(len(coords) - 1):
        x1 = coords[i][0] * meters_per_deg_lon
        y1 = coords[i][1] * meters_per_deg_lat
        x2 = coords[i+1][0] * meters_per_deg_lon
        y2 = coords[i+1][1] * meters_per_deg_lat
        area_sq_m += (x1 * y2) - (x2 * y1)

    area_sq_m = abs(area_sq_m) / 2.0
    # 1 hectare = 10,000 square meters
    area_hectares = max(0.01, round(area_sq_m / 10000.0, 4))

    return centroid_lat, centroid_lon, area_hectares


def generate_bounding_box(centroid_lat: float, centroid_lon: float, buffer_km: float = 1.0) -> List[float]:
    """Returns [min_lon, min_lat, max_lon, max_lat] for STAC / satellite search."""
    delta_lat = buffer_km / 111.0
    delta_lon = buffer_km / (111.0 * max(0.01, math.cos(math.radians(centroid_lat))))
    return [
        round(centroid_lon - delta_lon, 6),
        round(centroid_lat - delta_lat, 6),
        round(centroid_lon + delta_lon, 6),
        round(centroid_lat + delta_lat, 6)
    ]

import math
from typing import Any, Dict, Tuple
from shapely.geometry import Polygon, shape
from app.core.exceptions import InvalidGeometryException


class GeoService:
    @staticmethod
    def validate_and_compute_metrics(geojson_geom: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Validates GeoJSON polygon and computes centroid (lat, lon) and area in hectares.
        Ensures valid polygon, no self-intersections, coordinates within bounds, and area limits.
        """
        try:
            geom = shape(geojson_geom)
        except Exception as e:
            raise InvalidGeometryException(f"Failed to parse GeoJSON geometry: {str(e)}")

        if not isinstance(geom, Polygon):
            raise InvalidGeometryException(f"Expected Polygon geometry, received {geom.geom_type}")

        if not geom.is_valid:
            # Attempt minor repair via buffer(0)
            geom = geom.buffer(0)
            if not geom.is_valid or not isinstance(geom, Polygon):
                raise InvalidGeometryException("Polygon is invalid or contains self-intersections.")

        centroid = geom.centroid
        lat = float(centroid.y)
        lon = float(centroid.x)

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise InvalidGeometryException("Polygon centroid coordinates out of valid WGS84 range.")

        # Check vertex coordinates bounds
        for x, y in geom.exterior.coords:
            if not (-90.0 <= y <= 90.0) or not (-180.0 <= x <= 180.0):
                raise InvalidGeometryException(f"Vertex coordinates ({x}, {y}) out of valid WGS84 bounds.")

        # Ellipsoidal authalic conversion for area in square meters
        lat_rad = math.radians(lat)
        m_per_deg_lat = 111139.0
        m_per_deg_lon = 111139.0 * math.cos(lat_rad)

        coords = list(geom.exterior.coords)
        area_sq_m = 0.0
        for i in range(len(coords) - 1):
            x1 = coords[i][0] * m_per_deg_lon
            y1 = coords[i][1] * m_per_deg_lat
            x2 = coords[i + 1][0] * m_per_deg_lon
            y2 = coords[i + 1][1] * m_per_deg_lat
            area_sq_m += (x1 * y2) - (x2 * y1)

        area_sq_m = abs(area_sq_m) / 2.0
        area_ha = round(area_sq_m / 10000.0, 4)

        if area_ha < 0.005:
            raise InvalidGeometryException(f"Field area ({area_ha} ha) is below minimum threshold of 0.01 ha.")
        if area_ha > 50000.0:
            raise InvalidGeometryException(f"Field area ({area_ha} ha) exceeds single parcel limit of 50,000 ha.")

        return round(lat, 6), round(lon, 6), area_ha

    @staticmethod
    def create_square_polygon(lat: float, lon: float, side_meters: float = 100.0) -> Dict[str, Any]:
        """Creates a GeoJSON square polygon of side_meters centered around lat, lon."""
        half_side = side_meters / 2.0
        lat_rad = math.radians(lat)
        delta_lat = half_side / 111139.0
        delta_lon = half_side / (111139.0 * max(0.001, math.cos(lat_rad)))

        min_lon = round(lon - delta_lon, 6)
        max_lon = round(lon + delta_lon, 6)
        min_lat = round(lat - delta_lat, 6)
        max_lat = round(lat + delta_lat, 6)

        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]
            ],
        }

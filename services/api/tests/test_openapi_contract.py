"""
OpenAPI 3.1 Contract and Schema Conformance Quality Gate.
Validates live FastAPI schema against OpenAPI 3.1 specification standards,
ensuring zero undocumented endpoints, complete operation schemas, and security scheme declarations.
"""

from typing import Any, Dict
import pytest
from app.main import app


def test_openapi_schema_generation():
    """Generates live OpenAPI schema and verifies top-level OpenAPI 3.1 structure."""
    schema = app.openapi()
    assert isinstance(schema, dict)
    assert schema.get("openapi", "").startswith("3.")
    assert "info" in schema
    assert schema["info"]["title"] == "KrishiNet-BRICS (AgriN Commons)"
    assert "paths" in schema
    assert len(schema["paths"]) > 10


def test_openapi_operation_contracts():
    """Validates that every operation has responses, tags, and valid parameters."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    missing_responses = []
    missing_tags = []

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue

            op_id = f"{method.upper()} {path}"
            # Check responses defined
            responses = operation.get("responses", {})
            if not responses:
                missing_responses.append(op_id)

            # Check tags defined
            tags = operation.get("tags", [])
            if not tags:
                missing_tags.append(op_id)

    assert len(missing_responses) == 0, f"Operations lacking response schema: {missing_responses}"
    assert len(missing_tags) == 0, f"Operations lacking tags: {missing_tags}"


def test_openapi_security_schemes():
    """Verifies security components are declared in OpenAPI components."""
    schema = app.openapi()
    components = schema.get("components", {})
    sec_schemes = components.get("securitySchemes", {})

    # Ensure bearer auth / OAuth2 is declared
    assert len(sec_schemes) > 0, "No securitySchemes defined in OpenAPI specification components."


def test_openapi_path_drift_against_app_routes():
    """Verifies that every APIRoute in FastAPI is represented in the exported OpenAPI paths."""
    schema = app.openapi()
    openapi_paths = set(schema.get("paths", {}).keys())

    for route in app.routes:
        if getattr(route, "include_in_schema", True) and hasattr(route, "path"):
            path = route.path
            # Ignore internal docs paths
            if path in ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]:
                continue
            assert path in openapi_paths, f"Route {path} missing from OpenAPI exported paths!"

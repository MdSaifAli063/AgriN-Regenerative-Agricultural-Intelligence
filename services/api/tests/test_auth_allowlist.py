"""
Quality Gate: Zero-Unauthenticated Endpoints Guard.
Scans all FastAPI registered routes and fails if any route lacks an authentication
dependency unless it is explicitly permitted in the Sovereign Public Allow-List.
"""

from typing import Set
import pytest
from fastapi.routing import APIRoute
from app.main import app

# Strictly maintained sovereign public allow-list
EXPLICIT_PUBLIC_ALLOWLIST: Set[str] = {
    # Health and liveness probes
    "/health/live",
    "/health/ready",
    "/health/startup",
    # Open interoperability & Node Passport
    "/.well-known/agrin-node.json",
    "/stac",
    "/stac/collections",
    "/contexts/agrovoc.jsonld",
    # Inbound messaging webhooks & simulator (auth handled via signature / phone-hash)
    "/api/v1/webhooks/twilio",
    "/api/v1/webhooks/meta",
    "/api/v1/webhooks/africastalking",
    "/api/v1/messaging/simulate",
    # Public Auth endpoints
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/token",
    "/api/v1/auth/refresh",
    # Documentation & Schemas
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
}


def test_no_unauthenticated_endpoints():
    """
    Quality Gate: Scans every registered route on the FastAPI application.
    Asserts that every endpoint either:
    1. Has an authentication dependency (`get_current_user`, `get_admin_user`, `check_farm_ownership`), or
    2. Is explicitly declared in EXPLICIT_PUBLIC_ALLOWLIST.
    """
    unprotected_endpoints = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = route.path
        # Skip OpenAPI docs and redirects
        if path in EXPLICIT_PUBLIC_ALLOWLIST or path.rstrip("/") in EXPLICIT_PUBLIC_ALLOWLIST:
            continue

        # Check dependencies on the endpoint and route
        has_auth = False
        all_deps = list(route.dependencies)
        if hasattr(route, "endpoint") and hasattr(route.endpoint, "__annotations__"):
            # Check route parameters and dependencies
            for dep in route.dependant.dependencies:
                dep_name = dep.name or ""
                call_name = getattr(dep.call, "__name__", "")
                if any(k in call_name.lower() or k in dep_name.lower() for k in ["user", "auth", "token", "owner", "admin"]):
                    has_auth = True
                    break

        # Check route level dependencies
        for dep in route.dependant.all_dependencies:
            call_name = getattr(dep.call, "__name__", "")
            if any(k in call_name.lower() for k in ["user", "auth", "token", "owner", "admin", "security"]):
                has_auth = True
                break

        if not has_auth:
            unprotected_endpoints.append(f"{list(route.methods)} {path}")

    assert len(unprotected_endpoints) == 0, (
        f"CRITICAL SECURITY QUALITY GATE FAILURE: Found {len(unprotected_endpoints)} "
        f"unauthenticated endpoints not in explicit public allow-list:\n"
        + "\n".join(unprotected_endpoints)
    )

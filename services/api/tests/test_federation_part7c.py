"""
Part 7C Tests – OGC STAC API, JSON-LD Contexts, AGROVOC Resolver.

Tests:
  1. AGROVOC resolver loads mapping and resolves crop/pest/soil/practice terms.
  2. AGROVOC enrich_entity injects @context and AGROVOC URIs into domain payloads.
  3. STAC Landing Page is well-formed and contains mandatory conformance links.
  4. STAC /conformance lists mandatory OGC conformance classes.
  5. STAC /collections returns all 4 KrishiNet collections.
  6. STAC /collections/{id} returns a specific collection with items link.
  7. STAC /stac/search (GET) returns FeatureCollection with bbox filtering.
  8. STAC /stac/search (POST) returns filtered results.
  9. JSON-LD /contexts lists all 4 context files.
 10. AGROVOC verify_agrovoc script resolves all mandatory terms.
"""

import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "src"))
sys.path.insert(0, str(REPO_ROOT / "services" / "registry" / "src"))

from app.db.base import Base
from app.main import create_app
from app.core.deps import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.federation.agrovoc import AgrovocResolver

# Async integration tests use @pytest.mark.asyncio explicitly.

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def app_client(db_session):
    app = create_app()

    mock_user = User(
        id="test-user-7c",
        country_iso="IND",
        full_name="STAC Test User",
        phone_number="+919000000001",
        role="researcher",
    )

    async def override_db():
        yield db_session

    async def override_user():
        return mock_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ── AGROVOC Unit Tests ─────────────────────────────────────────────────────

def test_agrovoc_resolver_load():
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    resolver = AgrovocResolver(mapping_path=mapping_path)
    assert len(resolver._index) > 0, "AGROVOC index must be non-empty after load"


def test_agrovoc_crop_lookup():
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    resolver = AgrovocResolver(mapping_path=mapping_path)

    for crop in ["wheat", "rice", "maize", "soybean", "sorghum", "potato"]:
        result = resolver.lookup(crop, category="crops")
        assert result is not None, f"Crop '{crop}' must resolve from AGROVOC"
        assert result.get("uri", "").startswith("http://"), f"Crop '{crop}' must have a valid AGROVOC URI"
        assert result.get("agrovoc_id", "").startswith("c_"), f"Crop '{crop}' must have agrovoc_id"


def test_agrovoc_pest_lookup():
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    resolver = AgrovocResolver(mapping_path=mapping_path)

    for pest in ["fall_armyworm", "stem_rust", "rice_blast", "late_blight"]:
        result = resolver.lookup(pest, category="pests_and_diseases")
        assert result is not None, f"Pest '{pest}' must resolve"
        assert result.get("uri"), f"Pest '{pest}' must have URI"


def test_agrovoc_soil_lookup():
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    resolver = AgrovocResolver(mapping_path=mapping_path)

    for prop in ["organic_carbon", "ph", "nitrogen", "phosphorus", "potassium"]:
        result = resolver.lookup(prop, category="soil_properties")
        assert result is not None, f"Soil property '{prop}' must resolve"


def test_agrovoc_enrich_disease_diagnosis():
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    resolver = AgrovocResolver(mapping_path=mapping_path)

    payload = {
        "id": "diag-001",
        "crop": "wheat",
        "disease": "stem_rust",
        "confidence": 0.91,
        "severity": "high",
    }
    enriched = resolver.enrich_entity("disease_diagnosis", payload)
    assert enriched["@context"] == "/contexts/disease-diagnosis.jsonld"
    assert "crop_agrovoc_uri" in enriched
    assert enriched["crop_agrovoc_uri"].startswith("http://")
    assert "disease_agrovoc_uri" in enriched
    assert enriched["disease_agrovoc_uri"].startswith("http://")


def test_agrovoc_enrich_climate_analogue():
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    resolver = AgrovocResolver(mapping_path=mapping_path)

    payload = {
        "id": "ca-001",
        "recommended_crops": ["wheat", "sorghum", "unknown_crop_xyz"],
    }
    enriched = resolver.enrich_entity("climate_analogue", payload)
    assert enriched["@context"] == "/contexts/climate-analogue.jsonld"
    agrovoc_list = enriched.get("recommended_crops_agrovoc", [])
    assert isinstance(agrovoc_list, list)
    wheat_entry = next((e for e in agrovoc_list if e["crop"] == "wheat"), None)
    assert wheat_entry is not None
    assert wheat_entry["agrovoc_uri"] is not None
    # Unknown crop should still appear, just with null URI
    xyz_entry = next((e for e in agrovoc_list if e["crop"] == "unknown_crop_xyz"), None)
    assert xyz_entry is not None
    assert xyz_entry["agrovoc_uri"] is None


# ── STAC API Integration Tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stac_root(app_client):
    r = await app_client.get("/stac")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "Catalog"
    assert body["stac_version"] == "1.0.0"
    assert "conformsTo" in body
    assert any("stacspec" in c for c in body["conformsTo"])
    links = {lnk["rel"]: lnk for lnk in body["links"]}
    assert "data" in links
    assert "search" in links


@pytest.mark.asyncio
async def test_stac_conformance(app_client):
    r = await app_client.get("/stac/conformance")
    assert r.status_code == 200
    conforms = r.json()["conformsTo"]
    assert any("ogcapi-features" in c for c in conforms)


@pytest.mark.asyncio
async def test_stac_collections(app_client):
    r = await app_client.get("/stac/collections")
    assert r.status_code == 200
    body = r.json()
    collections = body["collections"]
    ids = {c["id"] for c in collections}
    assert "krishinet-outbreak-aggregates" in ids
    assert "krishinet-soil-intelligence" in ids
    assert "krishinet-climate-analogues" in ids
    assert "krishinet-model-cards" in ids
    for coll in collections:
        assert coll["license"] == "CC-BY-4.0"


@pytest.mark.asyncio
async def test_stac_collection_by_id(app_client):
    r = await app_client.get("/stac/collections/krishinet-outbreak-aggregates")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "Collection"
    assert body["id"] == "krishinet-outbreak-aggregates"
    link_rels = {lnk["rel"] for lnk in body["links"]}
    assert "items" in link_rels
    assert "alternate" in link_rels


@pytest.mark.asyncio
async def test_stac_collection_not_found(app_client):
    r = await app_client.get("/stac/collections/nonexistent-collection")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_stac_search_get(app_client):
    r = await app_client.get("/stac/search?collections=krishinet-outbreak-aggregates&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert isinstance(body["features"], list)
    # All returned features must have coarse centroids (≤2 decimal places)
    for feat in body["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Point":
            lon, lat = geom["coordinates"]
            assert round(lon, 2) == lon, f"lon {lon} has >2 decimal places"
            assert round(lat, 2) == lat, f"lat {lat} has >2 decimal places"


@pytest.mark.asyncio
async def test_stac_search_post(app_client):
    payload = {
        "collections": ["krishinet-outbreak-aggregates", "krishinet-soil-intelligence"],
        "limit": 20,
    }
    r = await app_client.post("/stac/search", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) <= 20


@pytest.mark.asyncio
async def test_stac_search_bbox_filter(app_client):
    # Bbox covering Indian subcontinent only
    r = await app_client.get("/stac/search?collections=krishinet-outbreak-aggregates&bbox=68,6,98,38")
    assert r.status_code == 200
    body = r.json()
    for feat in body["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        assert 68 <= lon <= 98, f"lon {lon} outside India bbox"
        assert 6 <= lat <= 38, f"lat {lat} outside India bbox"


@pytest.mark.asyncio
async def test_stac_items_collection(app_client):
    r = await app_client.get("/stac/collections/krishinet-outbreak-aggregates/items?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["context"]["limit"] == 5


# ── JSON-LD Context Endpoint Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_contexts_list(app_client):
    r = await app_client.get("/contexts")
    assert r.status_code == 200
    body = r.json()
    context_ids = {c["id"] for c in body["contexts"]}
    assert "soil-intelligence" in context_ids
    assert "disease-diagnosis" in context_ids
    assert "outbreak-aggregate" in context_ids
    assert "climate-analogue" in context_ids


@pytest.mark.asyncio
async def test_contexts_serve_jsonld(app_client):
    r = await app_client.get("/contexts/soil-intelligence.jsonld")
    assert r.status_code == 200
    assert "application/ld+json" in r.headers.get("content-type", "")
    body = r.json()
    assert "@context" in body
    ctx = body["@context"]
    assert "agrovoc" in ctx
    assert "organic_carbon" in ctx


@pytest.mark.asyncio
async def test_contexts_invalid_file(app_client):
    r = await app_client.get("/contexts/malicious-path-traversal.jsonld")
    assert r.status_code == 404


# ── AGROVOC Verify Script ──────────────────────────────────────────────────

def test_verify_agrovoc_script_all_resolved():
    """Verify that the agrovoc_mapping.json satisfies all mandatory terms."""
    mapping_path = REPO_ROOT / "data" / "seed" / "agrovoc_mapping.json"
    assert mapping_path.exists(), f"agrovoc_mapping.json must exist at {mapping_path}"

    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # Insert scripts dir into path for import
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import importlib
    spec = importlib.util.spec_from_file_location(
        "verify_agrovoc", REPO_ROOT / "scripts" / "verify_agrovoc.py"
    )
    verify_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verify_mod)
    EXPECTED_TERMS = verify_mod.EXPECTED_TERMS

    mappings = mapping.get("mappings", {})
    missing = []
    for category, terms in EXPECTED_TERMS.items():
        cat_data = mappings.get(category, {})
        for term in terms:
            entry = cat_data.get(term)
            if not entry or not entry.get("uri"):
                missing.append(f"{category}/{term}")

    assert not missing, f"Missing AGROVOC URIs: {missing}"


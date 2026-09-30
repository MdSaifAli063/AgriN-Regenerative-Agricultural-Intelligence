# KrishiNet-BRICS Interoperability Guide

> *One field. Many nations. Shared intelligence.*  
> Version 7F · Complete BRICS Commons Interoperability & Federation Suite · October 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Sovereign Data Residency Guarantees](#2-sovereign-data-residency-guarantees)
3. [OGC STAC 1.0.0 API](#3-ogc-stac-100-api)
4. [JSON-LD Contexts](#4-json-ld-contexts)
5. [FAO AGROVOC Semantic Mappings](#5-fao-agrovoc-semantic-mappings)
6. [OpenAPI 3.1 Schema Export](#6-openapi-31-schema-export)
7. [Node Passport (`.well-known`)](#7-node-passport-well-known)
8. [Federation Endpoints](#8-federation-endpoints)
9. [Consuming the API as an External Client](#9-consuming-the-api-as-an-external-client)
10. [Standards Compliance Matrix](#10-standards-compliance-matrix)

---

## 1. Overview

KrishiNet-BRICS operates as a **Sovereign Digital Public Good**: each BRICS member country runs an independent on-soil node (India `IND`, Brazil `BRA`, South Africa `ZAF`, China `CHN`, Russia `RUS`) that federates aggregated, anonymised intelligence through the BRICS Commons Registry without ever transmitting raw farmer PII, cadastral polygons, or leaf images across sovereign borders.

Interoperability is achieved through three complementary mechanisms:

| Layer | Standard | Purpose |
|---|---|---|
| **Spatial** | OGC STAC 1.0.0 | Discover & query agricultural intelligence items by bbox, datetime, collection |
| **Semantic** | JSON-LD + FAO AGROVOC | Linked data enrichment – resolve crop, pest, soil terms to multilingual thesaurus URIs |
| **Programmatic** | OpenAPI 3.1 | Machine-readable API contract for SDK/client generation |

---

## 2. Sovereign Data Residency Guarantees

All data leaving a KrishiNet node is subject to the **Sovereign Egress Gate** (`EgressGate`). The following constraints are enforced before any payload reaches the STAC API or Federation endpoints:

| Rule | Value | Notes |
|---|---|---|
| **Zero raw PII** | 100% | No phone numbers, emails, farmer IDs, survey numbers |
| **Coordinate precision** | ≤ 2 decimal places | ≈ 1.1 km regional centroid; localisation prevented |
| **k-Anonymity** | k ≥ 5 | Outbreak clusters with fewer than 5 observations are suppressed |
| **Laplace noise** | ε = 1.0 (optional) | Applied to case counts when k is close to threshold |
| **Bilateral agreement** | Required | Data flows only under active `FederationAgreement` records |
| **Audit log** | Immutable | Every egress attempt is SHA-256 hashed and stored in `EgressAuditLog` |

---

## 3. OGC STAC 1.0.0 API

### Base URLs

```
https://{country}.krishinet.org/stac        # node STAC endpoint
https://commons.krishinet.org/stac          # BRICS Commons aggregate (Phase 7F)
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/stac` | Root Catalog (landing page) |
| `GET` | `/stac/conformance` | OGC conformance classes |
| `GET` | `/stac/collections` | List all collections |
| `GET` | `/stac/collections/{id}` | Get collection metadata |
| `GET` | `/stac/collections/{id}/items` | List items in collection |
| `GET` | `/stac/search` | Item search with bbox, datetime, collections |
| `POST` | `/stac/search` | Item search (POST body) |

### Collections

| Collection ID | Content | Privacy Controls |
|---|---|---|
| `krishinet-outbreak-aggregates` | k-anonymised disease outbreak telemetry | k≥5, ≤2 d.p. coords |
| `krishinet-soil-intelligence` | ISRIC SoilGrids regional averages | regional centroid only |
| `krishinet-climate-analogues` | Cross-border climate similarity matches | country-level only |
| `krishinet-model-cards` | Federated ML model cards & provenance | no farmer data |

### Example: Search for outbreak aggregates in India

```bash
curl "https://ind.krishinet.org/stac/search" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["krishinet-outbreak-aggregates"],
    "bbox": [68.0, 6.0, 98.0, 38.0],
    "limit": 20
  }'
```

**Response fragment:**
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "krishinet-outbreak-aggregates-1",
    "geometry": { "type": "Point", "coordinates": [78.96, 20.59] },
    "bbox": [78.46, 20.09, 79.46, 21.09],
    "properties": {
      "datetime": "2026-10-01T00:00:00Z",
      "country_iso": "IND",
      "disease": "fall_armyworm",
      "disease_agrovoc_uri": "http://aims.fao.org/aos/agrovoc/c_16155",
      "crop": "maize",
      "crop_agrovoc_uri": "http://aims.fao.org/aos/agrovoc/c_4522",
      "case_count": 12,
      "severity": "moderate",
      "data_policy": {
        "k_anonymity": "≥5",
        "coordinate_precision": "≤2 decimal (~1.1 km)",
        "pii": "none"
      }
    },
    "collection": "krishinet-outbreak-aggregates"
  }]
}
```

> [!NOTE]
> All geometry coordinates are rounded to **exactly 2 decimal places** before serving. Coordinates with higher precision are rejected by the Sovereign Egress Gate.

### Conformance Classes

```json
{
  "conformsTo": [
    "https://api.stacspec.org/v1.0.0/core",
    "https://api.stacspec.org/v1.0.0/item-search",
    "https://api.stacspec.org/v1.0.0/item-search#fields",
    "https://api.stacspec.org/v1.0.0/item-search#filter",
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson"
  ]
}
```

---

## 4. JSON-LD Contexts

KrishiNet publishes four JSON-LD 1.1 context documents to make responses consumable by semantic-web tools (JSON-LD processors, RDF triplestores, schema.org crawlers).

### Serving Endpoints

| Context | URL | `@context` value in responses |
|---|---|---|
| Soil Intelligence | `/contexts/soil-intelligence.jsonld` | `/contexts/soil-intelligence.jsonld` |
| Disease Diagnosis | `/contexts/disease-diagnosis.jsonld` | `/contexts/disease-diagnosis.jsonld` |
| Outbreak Aggregate | `/contexts/outbreak-aggregate.jsonld` | `/contexts/outbreak-aggregate.jsonld` |
| Climate Analogue | `/contexts/climate-analogue.jsonld` | `/contexts/climate-analogue.jsonld` |

### Vocabularies Used

| Prefix | Namespace | Used for |
|---|---|---|
| `agrovoc:` | `http://aims.fao.org/aos/agrovoc/` | Crops, pests, soil properties |
| `sosa:` | `http://www.w3.org/ns/sosa/` | Observations, sensors, sampling |
| `ssn:` | `http://www.w3.org/ns/ssn/` | System properties |
| `schema:` | `https://schema.org/` | Date ranges, spatial coverage |
| `dcterms:` | `http://purl.org/dc/terms/` | Identifiers, created timestamps |
| `geojson:` | `https://purl.org/geojson/vocab#` | Coordinates |
| `krishinet:` | `https://krishinet.org/vocab#` | KrishiNet-specific terms |

### Example: Fetching a context

```bash
curl -H "Accept: application/ld+json" \
  https://ind.krishinet.org/contexts/soil-intelligence.jsonld
```

---

## 5. FAO AGROVOC Semantic Mappings

### Location

```
data/seed/agrovoc_mapping.json
```

### Structure

```json
{
  "$schema": "...",
  "version": "1.0.0",
  "mappings": {
    "crops": { "wheat": { "agrovoc_id": "c_8372", "uri": "http://...", "pref_label": { "en": "Wheat", "hi": "गेहूं" } } },
    "soil_properties": { ... },
    "pests_and_diseases": { ... },
    "regenerative_practices": { ... }
  }
}
```

### Verification Script

Run at any time (or in CI):

```bash
python scripts/verify_agrovoc.py          # report only
python scripts/verify_agrovoc.py --strict  # exit 1 if any term missing
```

Expected output when complete:
```
  Resolved : 43/43
  STATUS : ✓ ALL TERMS RESOLVED – mapping is complete.
```

### AGROVOC Enrichment

The `AgrovocResolver` class enriches domain payloads automatically:

```python
from app.federation.agrovoc import agrovoc_resolver

enriched = agrovoc_resolver.enrich_entity("disease_diagnosis", {
    "crop": "wheat",
    "disease": "stem_rust",
})
# Returns:
# {
#   "@context": "/contexts/disease-diagnosis.jsonld",
#   "crop": "wheat",
#   "crop_agrovoc_uri": "http://aims.fao.org/aos/agrovoc/c_8372",
#   "disease": "stem_rust",
#   "disease_agrovoc_uri": "http://aims.fao.org/aos/agrovoc/c_8373",
# }
```

---

## 6. OpenAPI 3.1 Schema Export

Generate and validate the full OpenAPI schema:

```bash
# JSON export with mandatory path validation
python scripts/export_openapi.py --output-dir docs --format json

# YAML export (requires pyyaml)
python scripts/export_openapi.py --output-dir docs --format yaml

# Both formats
python scripts/export_openapi.py --output-dir docs --format both
```

Outputs:
- `docs/openapi.json` – Full schema (importable into Postman, Insomnia, Stoplight)
- `docs/openapi_summary.md` – Markdown endpoint table

### Mandatory Interoperability Paths (validated automatically)

| Path | Methods |
|---|---|
| `/stac` | GET |
| `/stac/collections` | GET |
| `/stac/search` | GET, POST |
| `/contexts` | GET |
| `/contexts/{context_file}` | GET |
| `/.well-known/agrin-node.json` | GET |
| `/api/v1/federation/agreements` | GET, POST |
| `/api/v1/federation/egress/report` | GET |
| `/api/v1/federation/egress/dry-run` | POST |

---

## 7. Node Passport (`.well-known`)

Every KrishiNet sovereign node publishes a machine-readable Node Passport at:

```
GET /.well-known/agrin-node.json
```

**Response:**
```json
{
  "node_id": "IND-NODE-01",
  "country_code": "IND",
  "organisation_name": "KrishiNet Sovereign Node (IND)",
  "version": "1.0.0",
  "capabilities": ["stac-1.0.0", "geojson-rfc7946", "jsonld-agrovoc", "flower-fl-grpc", "mobilenetv3-disease-edge"],
  "standards_supported": ["OGC-STAC-1.0.0", "GeoJSON-RFC7946", "JSON-LD-AGROVOC", "OpenAPI-3.1", "Flower-FL"],
  "licences": ["Apache-2.0", "CC-BY-4.0"],
  "contact": "admin@krishinet.org",
  "data_policy": {
    "raw_data_residency": "100% on-soil",
    "egress_enforcement": "Sovereign Egress Gate with Differential Privacy and k-anonymity",
    "min_k_anonymity": 5,
    "max_coordinate_decimals": 2
  }
}
```

Also published at `/.well-known/agrin-registry.json` by the **BRICS Commons Registry** service.

---

## 8. Federation Endpoints

| Method | Path | RBAC Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/federation/agreements` | `government_admin` | List data-sharing agreements |
| `POST` | `/api/v1/federation/agreements` | `government_admin` | Create or counter-sign agreement |
| `POST` | `/api/v1/federation/egress/dry-run` | `government_admin` | Evaluate a payload against egress policy |
| `GET` | `/api/v1/federation/egress/report` | `government_admin` | "What leaves my country" compliance report |

---

## 9. Consuming the API as an External Client

### Discover Node Capabilities

```bash
curl https://ind.krishinet.org/.well-known/agrin-node.json
```

### Discover Available Collections

```bash
curl https://ind.krishinet.org/stac/collections
```

### Search Across Collections

```python
import httpx

r = httpx.post("https://ind.krishinet.org/stac/search", json={
    "collections": ["krishinet-outbreak-aggregates"],
    "bbox": [68.0, 6.0, 98.0, 38.0],
    "datetime": "2026-01-01T00:00:00Z/..",
    "limit": 50,
})
items = r.json()["features"]
```

### Resolve AGROVOC URIs

Each STAC item response includes AGROVOC URIs for crops and diseases:

```python
for item in items:
    props = item["properties"]
    print(props.get("crop_agrovoc_uri"))     # e.g. http://aims.fao.org/aos/agrovoc/c_4522
    print(props.get("disease_agrovoc_uri"))  # e.g. http://aims.fao.org/aos/agrovoc/c_16155
```

### Get JSON-LD Context

```python
import httpx, json

ctx_r = httpx.get("https://ind.krishinet.org/contexts/disease-diagnosis.jsonld")
ctx = ctx_r.json()["@context"]
```

---

## 10. Standards Compliance Matrix

| Standard | Version | Status | Notes |
|---|---|---|---|
| OGC STAC | 1.0.0 | ✅ Implemented | `/stac` root, collections, item search (GET+POST), bbox |
| OGC API Features | Part 1 | ✅ Conforms | GeoJSON output, conformance endpoint |
| JSON-LD | 1.1 | ✅ Implemented | 4 domain contexts with AGROVOC, SOSA/SSN, schema.org |
| FAO AGROVOC | 2024 | ✅ Implemented | 43/43 terms mapped – crops, pests, soil, practices |
| GeoJSON | RFC 7946 | ✅ Enforced | Point geometries, 2 d.p. coordinate coarsening |
| OpenAPI | 3.1.0 | ✅ Implemented | Full schema via `/openapi.json`, export script |
| Ed25519 | RFC 8032 | ✅ Implemented | Node identity signing (heartbeats, model cards, consent receipts) |
| Differential Privacy | Laplace/Gaussian | ✅ Implemented | ε=0.50 DP gradient noise in FL, Laplace ε=1.0 in outbreak aggregates |
| k-Anonymity | k ≥ 5 | ✅ Enforced | Hard gate in `EgressGate` |
| Flower FL | 1.10+ | ✅ Implemented | BricsFedAvgDP with Krum Byzantine defense & model hub bridge |
| Kantara Consent | v1.1.0 | ✅ Implemented | Sovereign farmer consent receipts & append-only SHA-256 ledger |
| Model Card Standard | 2026 BRICS | ✅ Implemented | Ed25519-signed ONNX model cards with weights SHA-256 digests |
| Apache License | 2.0 | ✅ | All code |
| Creative Commons | CC-BY-4.0 | ✅ | All published data |


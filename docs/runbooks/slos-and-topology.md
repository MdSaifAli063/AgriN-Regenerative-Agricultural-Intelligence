# Service Level Objectives (SLOs) & Sovereign Data Topology

This document formally states and justifies the Service Level Objectives (SLOs) for KrishiNet-BRICS and illustrates the sovereign multi-region cluster deployment topology.

---

## 1. Service Level Objectives (SLOs)

| Metric | Target | Error Budget (30-Day) | Justification & Rationale |
| :--- | :--- | :--- | :--- |
| **API Availability** | **99.5%** | 3.6 hours downtime | Farmers and extension officers operate in rural areas with intermittent connectivity. 99.5% ensures reliable service while allowing rolling updates and maintenance windows. |
| **Cached Read Latency (p95)** | **< 300 ms** | 5% of queries | Critical for mobile PWA usability over 2G/3G cellular links. Served via local Redis cache. |
| **Advisory Generation Latency (p95)** | **< 1,500 ms** | 5% of queries | Deterministic rules execute in < 250 ms. Hybrid Gemini synthesis is bounded to 1,500 ms before fallback triggers. |
| **Disease Diagnosis Latency (p95)** | **< 2,500 ms** | 5% of queries | Edge ONNX inference executes in < 300 ms; cloud ensemble verification completes within 2,500 ms. |
| **Advisory Freshness** | **< 24 Hours** | N/A | Telemetry snapshots (satellite NDVI, weather, soil) refresh daily to ensure farmers receive up-to-date agronomic actions. |
| **Messaging Delivery Latency (SMS/WhatsApp)**| **< 15 Seconds** | 1% delayed | Conversational FSM responses must arrive swiftly to maintain interactive chat pacing. |

---

## 2. Sovereign Multi-Cluster Topology Architecture

### Core Data Sovereignty Principle:
- **Each sovereign nation (India, Brazil, South Africa, etc.) runs its own dedicated Kubernetes cluster and PostgreSQL database located strictly within national borders.**
- **Farmer identities, raw soil metrics, farm polygons, and disease photos NEVER leave the national cluster.**
- **The BRICS Central Registry runs in a neutral cluster and stores ONLY anonymous aggregated model cards, differential-privacy model weights, and node metadata. It holds ZERO farmer personal data.**

```mermaid
flowchart TB
    subgraph CentralRegistry["BRICS Agricultural Commons (Neutral Zone)"]
        RegistryAPI["BRICS Model Hub & Registry API<br/>(registry.brics.agri)"]
        CoordServer["Flower Federated Coordinator"]
        ModelCards[("Model Cards & Aggregated Stats<br/>(ZERO Farmer Data)")]
    end

    subgraph IndiaNode["India Sovereign Node (ICAR Cluster - Mumbai)"]
        IN_Ingress["Nginx Ingress + TLS"]
        IN_API["FastAPI Node API"]
        IN_Worker["Celery Worker + Beat"]
        IN_DB[("PostgreSQL 16 + PostGIS + pgvector<br/>(Indian Farmer Data)")]
        IN_MinIO[("MinIO S3 Assets")]
        IN_Keys["Ed25519 Node Private Key"]
        IN_Egress{"Sovereign Egress Gate<br/>(k-Anonymity >= 5, DP ε=1.0)"}
    end

    subgraph BrazilNode["Brazil Sovereign Node (EMBRAPA Cluster - São Paulo)"]
        BR_Ingress["Nginx Ingress + TLS"]
        BR_API["FastAPI Node API"]
        BR_DB[("PostgreSQL 16 + PostGIS + pgvector<br/>(Brazilian Farmer Data)")]
        BR_Keys["Ed25519 Node Private Key"]
        BR_Egress{"Sovereign Egress Gate<br/>(k-Anonymity >= 5, DP ε=1.0)"}
    end

    subgraph SouthAfricaNode["South Africa Sovereign Node (ARC Cluster - Pretoria)"]
        ZA_Ingress["Nginx Ingress + TLS"]
        ZA_API["FastAPI Node API"]
        ZA_DB[("PostgreSQL 16 + PostGIS + pgvector<br/>(South African Farmer Data)")]
        ZA_Keys["Ed25519 Node Private Key"]
        ZA_Egress{"Sovereign Egress Gate<br/>(k-Anonymity >= 5, DP ε=1.0)"}
    end

    %% National Ingress
    IN_Ingress --> IN_API
    IN_API --> IN_DB
    IN_API --> IN_Worker
    IN_API --> IN_MinIO

    BR_Ingress --> BR_API
    BR_API --> BR_DB

    ZA_Ingress --> ZA_API
    ZA_API --> ZA_DB

    %% Federated Egress Perimeter
    IN_API --> IN_Egress
    IN_Keys -.-> IN_Egress
    IN_Egress -- "Signed Model Weights (DP ε)" --> CoordServer

    BR_API --> BR_Egress
    BR_Keys -.-> BR_Egress
    BR_Egress -- "Signed Model Weights (DP ε)" --> CoordServer

    ZA_API --> ZA_Egress
    ZA_Keys -.-> ZA_Egress
    ZA_Egress -- "Signed Model Weights (DP ε)" --> CoordServer

    CoordServer --> RegistryAPI
    RegistryAPI --> ModelCards

    classDef sovereign fill:#1b4332,stroke:#40916c,stroke-width:2px,color:#fff;
    classDef neutral fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#fff;
    class IndiaNode,BrazilNode,SouthAfricaNode sovereign;
    class CentralRegistry neutral;
```

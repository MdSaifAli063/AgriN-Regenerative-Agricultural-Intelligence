# Onboard a New Sovereign Nation Node (< 1 Day SLA)

> **KrishiNet-BRICS Digital Public Good (DPG) Deployment Guide**  
> Target Audience: National Ministries of Agriculture, Digital Transformation Agencies, National Research Councils (e.g., ICAR, Embrapa, ARC, CAAS).  
> Standard Time to Production: **Under 4 Hours**.

---

## 1. Executive Summary & Sovereignty Principles

KrishiNet-BRICS is architected as an **Interoperable Sovereign Digital Public Good**. When a new country joins the federation, **100% of raw farmer data remains on sovereign national soil**:
- Farmer identities, telephone numbers, and cadastral GPS boundaries **never** cross sovereign borders.
- Raw crop leaf photos remain within the national MinIO object store.
- Only **k-anonymised telemetry** (k ≥ 5), **coarsened regional centroids** (≤ 2 decimal places), **differentially private AI gradients**, and **open Digital Public Good (DPG) model cards** are exchanged through the BRICS Commons Registry.

---

## 2. Prerequisites & Infrastructure Sizing

Each sovereign node runs independently within your national cloud or on-premise government data center.

### Minimum Hardware Specification (Single-Node Dev / Pilot)
- **CPU**: 4 vCPUs
- **Memory**: 8 GB RAM
- **Disk**: 100 GB NVMe SSD
- **Network**: 50 Mbps outbound HTTPS (Port 443)
- **OS**: Ubuntu 22.04 LTS, Debian 12, or RHEL 9
- **Container Runtime**: Docker Engine 24+ & Docker Compose v2 (or Kubernetes 1.28+)

### Production High-Availability Cluster (Recommended)
- Kubernetes 1.28+ with Helm 3.12+
- Managed PostgreSQL 16 with PostGIS 3.4 & pgvector
- S3-compatible Sovereign Object Store (MinIO Enterprise, Ceph, or National Cloud S3)
- Ingress controller with automated TLS (Cert-Manager / Let's Encrypt / National CA)

---

## 3. Step-by-Step Onboarding Workflow

### Step 3.1: Generate Sovereign Ed25519 Cryptographic Identity

Every node is cryptographically identified by an Ed25519 keypair. The private key never leaves the node server.

```bash
# 1. Clone the KrishiNet-BRICS repository
git clone https://github.com/krishinet/krishinet-brics.git /opt/krishinet
cd /opt/krishinet

# 2. Generate sovereign keypair for your country (Example: Ethiopia - ETH)
python3 -c "
from pathlib import Path
from app.federation.identity import NodeIdentity
keys_dir = Path('.node_keys')
node = NodeIdentity.load_or_create(keys_dir, 'node-eth-eiar-01', country_code='ETH')
print(f'Node ID:    {node.node_id}')
print(f'Country:    {node.country_code}')
print(f'Public Key: {node.public_key_hex}')
"
```

Save the printed **Public Key (Hex)** — you will share this with the BRICS Commons Registry.

---

### Step 3.2: Configure Sovereign Environment Variables

Copy `.env.example` to `.env` and configure your sovereign node identity:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Core Configuration
ENVIRONMENT=production
DEMO_MODE=false
DEV_AUTH_BYPASS=false

# Sovereign Node Identity
NODE_ID=node-eth-eiar-01
LOCAL_NODE_COUNTRY_ISO=ETH
NODE_NAME=Ethiopia (EIAR / Ministry of Agriculture)
NODE_BASE_URL=https://eth.krishinet.org

# BRICS Commons Registry Connection
REGISTRY_URL=https://commons.krishinet.org
REGISTRY_PUBLIC_KEY_HEX=<OFFICIAL_REGISTRY_PUBLIC_KEY>

# Sovereign Egress Gate (Enforce Strict Data Sovereignty)
EGRESS_STRICT_MODE=true
MIN_K_ANONYMITY=5
MAX_COORDINATE_DECIMALS=2
LAPLACE_DP_EPSILON=1.0

# Federated Learning (Flower)
FLOWER_NUM_ROUNDS=3
FLOWER_DP_EPSILON=0.50
FLOWER_DP_DELTA=1e-5
```

---

### Step 3.3: Deploy Sovereign AgriN Node

#### Option A: Docker Compose Deployment (Quickstart)
```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
python3 scripts/seed.py --country ETH
```

#### Option B: Kubernetes / Helm Deployment (Production)
```bash
helm upgrade --install agrin-node-eth ./infra/helm/agrin-node \
  --namespace agrin-system --create-namespace \
  --set node.id="node-eth-eiar-01" \
  --set node.countryIso="ETH" \
  --set node.name="Ethiopia (EIAR)" \
  --set node.registryUrl="https://commons.krishinet.org" \
  --set ingress.hosts[0].host="eth.krishinet.org" \
  --set networkPolicy.enabled=true
```

---

### Step 3.4: Register Node in BRICS Commons Registry

Execute the mutual cryptographic handshake to register your public key in the Commons Registry:

```bash
curl -X POST "https://commons.krishinet.org/api/v1/registry/nodes/register" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-eth-eiar-01",
    "country_code": "ETH",
    "country_name": "Ethiopia",
    "organisation_name": "Ethiopian Institute of Agricultural Research (EIAR)",
    "base_url": "https://eth.krishinet.org",
    "public_key_hex": "<YOUR_PUBLIC_KEY_HEX>",
    "capabilities": [
      "stac-1.0.0",
      "jsonld-agrovoc",
      "flower-fl-grpc",
      "mobilenetv3-disease-edge"
    ]
  }'
```

---

### Step 3.5: Execute Bilateral Data Sharing Agreements

Activate data exchange scopes with partner nodes (e.g., India, Brazil, South Africa):

```bash
curl -X POST "https://eth.krishinet.org/api/v1/federation/agreements" \
  -H "Authorization: Bearer <GOV_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "partner_node_id": "node-ind-icar-01",
    "partner_country_code": "IND",
    "scope": "crop_models_and_climate_analogues",
    "data_licence": "CC-BY-4.0",
    "valid_until": "2028-12-31T23:59:59Z"
  }'
```

---

## 4. Verification & Health Checklist

Verify your node passes all 5 sovereign compliance criteria:

| Step | Test Command | Expected Result |
|---|---|---|
| **1. Node Passport** | `curl https://eth.krishinet.org/.well-known/agrin-node.json` | Valid JSON with `raw_data_residency: "100% on-soil"` |
| **2. STAC Catalog** | `curl https://eth.krishinet.org/stac` | Conforming OGC STAC 1.0.0 Catalog |
| **3. AGROVOC Mapping**| `python3 scripts/verify_agrovoc.py --strict` | `✓ ALL TERMS RESOLVED (43/43)` |
| **4. Egress Gate Test**| `curl -X POST https://eth.krishinet.org/api/v1/federation/egress/dry-run` | `passed: true` on anonymized, `blocked` on PII |
| **5. Consent Ledger** | `curl https://eth.krishinet.org/api/v1/consents/verify-ledger` | `is_valid: true, integrity_status: "VERIFIED"` |

---

## 5. Security & Sovereignty Guarantees

1. **Air-Gapped Sovereign Fallback**: If the central registry is unreachable, your node continues serving local farmers, computing offline NDVI satellite indices, and diagnosing crop diseases via edge ONNX inference.
2. **Kantara-Compliant Consent Ledger**: Every farmer data grant or revocation is signed and recorded in an immutable SHA-256 hash-chain. Revocations take effect immediately.
3. **Byzantine Fault Tolerance**: Federated learning runs with Krum trimmed-mean defenses, preventing malicious nodes from corrupting shared AI models.

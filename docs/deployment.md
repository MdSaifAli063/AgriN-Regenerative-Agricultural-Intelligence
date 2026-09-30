# KrishiNet-BRICS — Production & Demonstration Deployment Guide

This guide details three battle-tested deployment tracks for KrishiNet-BRICS:
1. **Track A ("Live Demo in Under an Hour")**: Cheapest & fastest path utilizing modern serverless/PaaS free tiers.
2. **Track B ("Single VM / Small Team")**: Docker Compose + Caddy (automatic HTTPS) on a $20–$40/mo 4 GB VPS with the `federation-lite` profile.
3. **Track C ("Enterprise / Sovereign Kubernetes")**: Production-grade Helm charts, CloudNativePG, External Secrets Operator, and the full Observability Stack on K3s or managed EKS/GKE/AKS.

---

## Track A: "Live Demo in Under an Hour" (Serverless / PaaS Free Tier)

**Total Estimated Setup Time**: 45–60 minutes  
**Estimated Monthly Cost**: **$0.00 – $5.00** (fits completely within free tiers)

```
[Vercel: Next.js PWA] ---> [Render / Railway / Fly.io: FastAPI] ---> [Neon / Supabase: Postgres + PostGIS + pgvector]
                                     |                                         |
                                     +---> [Upstash: Serverless Redis]        +---> [Cloudflare R2: S3 Object Storage]
                                     |
                                     +---> [Twilio WhatsApp Sandbox + Cloudflare Tunnel]
```

### 1. Database Setup: Neon or Supabase (Postgres 16 + PostGIS + pgvector)
1. Sign up for a free project at [Neon.tech](https://neon.tech) or [Supabase.com](https://supabase.com).
2. Open the SQL Editor and enable the required spatial and vector extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```
3. Copy your connection string (format: `postgresql+asyncpg://user:pass@ep-xyz.neon.tech/neondb?ssl=require`).

### 2. Cache & Task Queue: Upstash Redis
1. Create a free serverless Redis database at [Upstash.com](https://upstash.com).
2. Copy the `REDIS_URL` connection string (format: `rediss://default:token@xyz.upstash.io:6379`).

### 3. S3 Asset Storage: Cloudflare R2 or Supabase Storage
1. In Cloudflare Dashboard, navigate to **R2** > **Create Bucket** named `krishinet-assets`.
2. Generate an S3 API token with Read/Write permissions.
3. Our `StorageService` (`app/services/storage.py`) supports S3-compatible endpoints directly via environment variables:
   ```env
   MINIO_ENDPOINT="<account_id>.r2.cloudflarestorage.com"
   MINIO_ROOT_USER="<r2_access_key_id>"
   MINIO_ROOT_PASSWORD="<r2_secret_access_key>"
   MINIO_SECURE=true
   MINIO_BUCKET_NAME="krishinet-assets"
   ```

### 4. Backend API & Celery Worker: Render / Railway / Fly.io
Deploy using the root `Dockerfile` or Render Web Service:
- **Build Command**: `pip install -r services/api/requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Environment Variables**:
  ```env
  DEMO_MODE=true
  DEV_AUTH_BYPASS=true
  ENVIRONMENT=staging
  DATABASE_URL=postgresql+asyncpg://...
  REDIS_URL=rediss://...
  GEMINI_API_KEY=<your_google_gemini_api_key>
  DEFAULT_MESSAGING_PROVIDER=simulator # or twilio
  MESSAGING_ENCRYPTION_KEY="MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="
  ```

### 5. Frontend PWA: Vercel
1. Import the repository into Vercel and set Root Directory to `apps/web`.
2. Environment Variables:
   ```env
   NEXT_PUBLIC_API_URL=https://<your-render-app>.onrender.com
   NEXT_PUBLIC_DEMO_MODE=true
   NEXT_PUBLIC_COUNTRY_ISO=IND
   ```
3. Deploy. The web application will be live at `https://<your-app>.vercel.app`.

### 6. Free-Tier Gotchas & Mitigations
| Free-Tier Limitation | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Cold Starts** (Render / Fly free tier spins down after 15m idle) | 30s delay on first request | Set up a free UptimeRobot or Cron keep-warm ping hitting `/health/live` every 5 minutes. |
| **Memory Limit** (512 MB on free containers) | Potential OOM on heavy ONNX runtime or GeoTIFF rasterization | Run ML inference in `DEMO_MODE=true` (uses lightweight mock or edge ONNX with low memory footprint). |
| **Request Timeout** (30s on Render/Vercel) | Long AI generations time out | Long-running advisory tasks run in Celery background workers returning a `task_id`. |

---

## Track B: "Single VM" (Docker Compose + Caddy on 4 GB VPS)

**Total Estimated Setup Time**: 20–30 minutes  
**Estimated Monthly Cost**: **$20.00 – $40.00/mo** (Hetzner / DigitalOcean / Linode 4 GB VPS)

Track B is ideal for sovereign national field demos and pilot trials without Kubernetes overhead.

### 1. Provision Ubuntu 22.04 / 24.04 VPS
```bash
# Connect to your VPS
ssh root@<vps_ip>

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com | sh
apt-get update && apt-get install -y git ufw unattended-upgrades

# Configure UFW Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
```

### 2. Clone Repository & Configure Environment
```bash
git clone https://github.com/krishinet/krishinet-brics.git /opt/krishinet
cd /opt/krishinet
cp .env.example .env
nano .env # Set your domain, GEMINI_API_KEY, and passwords
```

### 3. Launch with Docker Compose (`federation-lite` Profile)
```bash
# Pull and start services in background
docker compose --profile federation-lite up -d --build

# Run database migrations
docker compose exec api alembic upgrade head

# Run smoke test verification
./scripts/smoke.sh
```

### 4. Automatic HTTPS with Caddy
Caddy automatically provisions and renews Let's Encrypt certificates. Add to `/etc/caddy/Caddyfile`:
```caddy
node.krishinet.brics.agri {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /docs localhost:8000
    reverse_proxy /openapi.json localhost:8000
    reverse_proxy /* localhost:3000
}
```
Reload Caddy: `systemctl reload caddy`.

---

## Track C: "Kubernetes" (Production & Sovereign Multi-Cluster)

**Total Estimated Setup Time**: 1–2 hours  
**Target Environments**: K3s (Bare-Metal / Single Node) or Managed K8s (GKE / EKS / AKS)

Track C delivers full multi-replica scalability, automated HPA, PodDisruptionBudgets, CloudNativePG streaming replication, and the OpenTelemetry observability suite.

### 1. Install Helm & Cert-Manager
```bash
# Install Cert-Manager for Let's Encrypt TLS
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true
```

### 2. Deploy CloudNativePG Operator (Database HA)
```bash
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm upgrade --install cnpg cnpg/cloudnative-pg \
  --namespace cnpg-system --create-namespace

# Apply sovereign PostgreSQL cluster with PostGIS + pgvector
kubectl apply -f infra/k8s/cloudnative-pg-cluster.yaml
```

### 3. Deploy External Secrets Operator
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace

# Apply Vault / KMS secret mappings
kubectl apply -f infra/k8s/external-secrets.yaml
```

### 4. Deploy Sovereign Node via Helm
```bash
# Install national node chart with country-specific values (e.g. India)
helm upgrade --install agrin-node-ind infra/helm/agrin-node \
  --namespace agrin-node --create-namespace \
  -f infra/helm/agrin-node/values.yaml \
  -f infra/helm/agrin-node/values-prod.yaml \
  -f infra/helm/agrin-node/values-in.yaml

# Check rollout status
kubectl rollout status deployment/agrin-node-ind-api -n agrin-node
```

### 5. Deploy Observability Stack
```bash
# Apply Prometheus Alert Rules and ServiceMonitors
kubectl apply -f infra/observability/prometheus-servicemonitors.yaml
kubectl apply -f infra/observability/alert-rules.yaml
kubectl apply -f infra/observability/otel-collector-config.yaml
```

---

## Production Go-Live Checklist

Before transitioning from `DEMO_MODE=true` to public live production:

- [ ] **Security & Authentication**:
  - [ ] `DEV_AUTH_BYPASS` is set to `false`.
  - [ ] `DEMO_MODE` set to `false` for live national pilot.
  - [ ] Default passwords and keys in `.env` rotated.
  - [ ] Ed25519 node private key generated in secure air-gapped HSM and mounted as read-only volume.
  - [ ] Webhook signatures verified (`X-Twilio-Signature`, `X-Hub-Signature-256`).
- [ ] **Network & Perimeter**:
  - [ ] Strict NetworkPolicies active in `agrin-node` namespace (zero unauthorized egress).
  - [ ] Ingress TLS verified with A+ rating on SSLLabs.
  - [ ] Rate limits configured at Ingress (`limit-rps: 50`) and application middleware.
  - [ ] Maximum body size restricted (`client_max_body_size: 25m`) for leaf image uploads.
- [ ] **Data Sovereignty & Legal Compliance**:
  - [ ] Kantara-compliant consent receipts and immutable audit ledger active.
  - [ ] "Delete My Data" (Right to be Forgotten) procedure tested and verified.
  - [ ] 30-day message body retention purge task enabled in Celery Beat.
  - [ ] Privacy Policy and Terms of Service pages published in all 12 supported locales.
- [ ] **Backups & Disaster Recovery**:
  - [ ] Nightly encrypted `pg_dump` CronJob running and verified.
  - [ ] Disaster recovery restore drill (`scripts/restore_drill.sh`) executed with RTO < 15m.
- [ ] **Observability**:
  - [ ] OpenTelemetry collector active with PII coordinate scrubber processor.
  - [ ] Prometheus alert rules for error budget burn and budget threshold active.

# KrishiNet-BRICS — CI/CD Secrets & Variables Architecture

This document defines the complete matrix of **GitHub Environments**, **Repository Secrets**, and **Configuration Variables** utilized across all automated CI/CD workflows (`ci.yml`, `security.yml`, `build.yml`, `deploy-staging.yml`, `release.yml`).

---

## 1. GitHub Environments & Protection Rules

| Environment | Purpose | Protection Rules & Approvals | Deployed URL |
| :--- | :--- | :--- | :--- |
| **`development`** | Ephemeral PR test runners with service containers | None (automated run on all PRs) | `http://localhost:8000` |
| **`staging`** | Continuous integration target for `main` branch | Auto-deployment; automated rollback on `smoke.sh` failure | `https://staging.krishinet.brics.agri` |
| **`production`** | Live sovereign national clusters | Required Reviewers: **KrishiNet Security Lead + National Cluster Admin** | `https://krishinet.brics.agri` |

---

## 2. Secrets Matrix (GitHub Actions Secrets)

| Secret Name | Scope / Environment | Workflow Used In | Purpose & Description | Rotation Policy |
| :--- | :--- | :--- | :--- | :--- |
| `GITHUB_TOKEN` | Global (Built-in) | `ci.yml`, `security.yml`, `build.yml`, `release.yml` | GHCR container publishing, release asset uploads, Gitleaks PR comments | Auto-rotated by GitHub per workflow run |
| `STAGING_KUBECONFIG` | Environment: `staging` | `deploy-staging.yml` | Base64-encoded Kubeconfig credentials for staging Kubernetes cluster | 90 days |
| `PROD_KUBECONFIG` | Environment: `production` | Production CD | Base64-encoded Kubeconfig credentials for sovereign national nodes | 90 days |
| `MESSAGING_ENCRYPTION_KEY` | Global / Staging / Prod | `ci.yml`, Staging runtime, Prod runtime | 32-byte Base64 Fernet key used to encrypt farmer phone numbers for outbound alerts | 180 days (re-encryption required) |
| `GEMINI_API_KEY` | Environment: `staging`, `production` | Runtime deployments | Google Gemini Flash / Vision API key for multilingual advisory and leaf pathology | 90 days |
| `TWILIO_ACCOUNT_SID` | Environment: `staging`, `production` | Runtime messaging gateway | Twilio Account SID for India / global SMS & WhatsApp sandboxes | 180 days |
| `TWILIO_AUTH_TOKEN` | Environment: `staging`, `production` | Runtime messaging gateway | Twilio Auth Token for webhook signature verification (`X-Twilio-Signature`) | 90 days |
| `META_ACCESS_TOKEN` | Environment: `staging`, `production` | Runtime messaging gateway | System user access token for WhatsApp Cloud API (Brazil / Latin America) | 60 days |
| `META_APP_SECRET` | Environment: `staging`, `production` | Runtime messaging gateway | Meta App Secret for SHA-256 HMAC webhook verification (`X-Hub-Signature-256`) | 180 days |
| `AFRICASTALKING_API_KEY`| Environment: `staging`, `production` | Runtime messaging gateway | Africa's Talking API key for low-cost SMS in South Africa, Ethiopia, Egypt | 90 days |
| `KEYCLOAK_CLIENT_SECRET`| Environment: `staging`, `production` | API Runtime Auth | OIDC client secret for Keycloak federated SSO authentication | 180 days |
| `JWT_SECRET_KEY` | Environment: `staging`, `production` | API Runtime Auth | HS256 secret key for signing internal microservice session tokens | 90 days |
| `NODE_PRIVATE_KEY_ED25519` | Staging / Prod (Volume Mount) | Federation Runtime | Ed25519 private key for signing model updates in Flower federated learning rounds | 365 days (requires node re-registration) |

---

## 3. Configuration Variables Matrix (GitHub Actions Variables)

| Variable Name | Default Value | Recommended Staging | Recommended Production | Description |
| :--- | :--- | :--- | :--- | :--- |
| `DEMO_MODE` | `true` | `true` | `false` | When `true`, enables offline fallback for Gemini, Twilio, and external APIs. |
| `DEV_AUTH_BYPASS` | `true` | `false` | `false` | **MUST BE `false` IN PRODUCTION.** Allows `/api/v1/auth/dev-login` endpoint. |
| `COUNTRY_ISO` | `IND` | `IND` | Per sovereign cluster (`IND`, `BRA`, `ZAF`) | National node country code. |
| `DEFAULT_MESSAGING_PROVIDER` | `simulator` | `simulator` | `twilio` (IND) / `meta` (BRA) / `africastalking` (ZAF) | Active messaging provider for outbound alerts. |
| `MESSAGING_RETENTION_DAYS` | `30` | `14` | `30` | Number of days inbound and outbound message bodies are retained before purge. |
| `API_URL` | `http://localhost:8000` | `https://staging-api.krishinet.brics.agri` | `https://api.krishinet.brics.agri` | API base URL for smoke tests and web client requests. |
| `REGISTRY_URL` | `http://localhost:8001` | `https://staging-registry.krishinet.brics.agri` | `https://registry.brics.agri` | Neutral BRICS model registry URL. |

---

## 4. Least-Privilege GitHub Actions Permissions Architecture

Every workflow in `.github/workflows/` explicitly defines minimal permissions:

```yaml
# Example: ci.yml
permissions:
  contents: read          # Read source code only
  pull-requests: read     # Read PR context for path filtering
  checks: write           # Post test result annotations

# Example: build.yml
permissions:
  contents: read          # Read source code
  packages: write         # Publish container images to GHCR
  id-token: write         # Obtain OIDC token for Cosign keyless signing
  attestations: write     # Generate SLSA provenance attestations

# Example: release.yml
permissions:
  contents: write         # Create GitHub Release and upload artifacts
  packages: read          # Read packages for verification
```

---

## 5. Security & Secret Rotation Runbook

1. **Compromised Provider Secret**:
   - Rotate API key immediately in Twilio/Meta/Africa's Talking console.
   - Update the respective secret in GitHub Environment (`staging` / `production`).
   - Trigger rolling restart of Kubernetes deployment: `kubectl rollout restart deployment/agrin-node-api -n <namespace>`.
2. **Rotating `MESSAGING_ENCRYPTION_KEY`**:
   - Generate new 32-byte Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
   - Run the database re-encryption migration script to re-encrypt stored phone numbers with the new key.
   - Update the GitHub secret and restart worker pods.

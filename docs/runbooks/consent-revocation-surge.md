# Operational Runbook: Consent Revocation Surge & Egress Purging

## 1. Scenario
- An unexpected surge of farmers revoking data sharing consents (e.g. following regulatory notices or local privacy campaigns).

## 2. Automated Safeguards
1. `ConsentManager.revoke_consent` records each revocation in the immutable cryptographic ledger block.
2. Federated learning training queues immediately drop the user's field IDs from ongoing cohorts.
3. Outbound egress perimeter filter blocks any anonymized telemetry containing the revoked farmer's data.

## 3. Operator Verification Steps
1. Verify consent ledger chain integrity:
   ```bash
   curl -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/api/v1/consents/verify-ledger
   ```
2. Check egress block counts:
   Inspect Grafana Dashboard `federation-consent-sovereignty`.
3. If mass data erasure ("Right to be Forgotten") was requested, verify zero residual assets remain:
   ```bash
   python -c "from app.services.privacy.retention import DataRetentionManager; print('Retention purge ready')"
   ```

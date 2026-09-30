# Operational Runbook: Gemini API Outage / Degraded Mode

## 1. Alert Trigger
- **Alert**: `KrishiNetGeminiOverloaded` or HTTP 503 / 429 errors from `generativelanguage.googleapis.com`.
- **Impact**: AI explanations, dynamic advisory enrichment, and cloud vision fallback are unavailable.

## 2. Automated System Behavior
1. `ExternalServiceGuard` detects failure and trips circuit breaker after 3 consecutive failures.
2. System immediately switches `EngineMode` to `RULES_ONLY` via `DeterministicRuleEngine`.
3. Advisories continue generating deterministically from local biophysical rules (soil pH, SOC, weather metrics).
4. Farmers receive the degraded mode banner: *"AI dynamic synthesis temporarily unavailable. Advisory generated using verified agronomic extension rules."*
5. Disease detection falls back strictly to local ONNX edge model inference (`ml/edge_inference.py`).

## 3. Operator Action Steps
1. **Verify Circuit Breaker Status**:
   ```bash
   curl -s http://localhost:8000/api/v1/health/ready | jq .
   ```
2. **Force Offline / Rules-Only Mode**:
   If Gemini is experiencing intermittent hanging/timeouts without 503:
   ```bash
   kubectl set env deployment/agrin-node-api DEMO_MODE=true -n agrin-node
   ```
3. **Check Quota & Token Spend**:
   Check Google Cloud Console or Grafana Dashboard: `celery-messaging-pipeline`.
4. **Recovery & Re-enablement**:
   When Google Cloud resolves the incident, verify connectivity:
   ```bash
   curl -I https://generativelanguage.googleapis.com/
   kubectl set env deployment/agrin-node-api DEMO_MODE=false -n agrin-node
   ```

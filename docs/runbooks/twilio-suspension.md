# Operational Runbook: Twilio / Messaging Provider Suspension

## 1. Alert Trigger
- **Alert**: `KrishiNetMessagingProviderDown` (Outbound failure rate > 15% or HTTP 403 Account Suspended).
- **Impact**: Outbound morning alerts and WhatsApp advisory responses cannot be dispatched via Twilio.

## 2. Immediate Operator Mitigation
1. **Switch Active Node Provider**:
   KrishiNet supports dynamic multi-provider routing without application downtime.
   To switch India node from Twilio to Africa's Talking / Simulator:
   ```bash
   kubectl set env deployment/agrin-node-api DEFAULT_MESSAGING_PROVIDER=simulator -n agrin-node
   kubectl set env deployment/agrin-node-worker DEFAULT_MESSAGING_PROVIDER=simulator -n agrin-node
   ```
2. **Inspect Dead-Letter Queue**:
   Query undelivered messages trapped during the suspension:
   ```bash
   curl -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/api/v1/broadcasts/dead-letter
   ```
3. **Re-queue Dead-Letter Messages**:
   Once alternate provider credentials or account reactivation is complete, flush DLQ through Celery background task: `app.messaging.tasks.replay_dead_letters`.

# Operational Runbook: Database Primary Node Failover

## 1. Alert Trigger
- **Alert**: `PostgresClusterDegraded` or `PGPrimaryUnreachable`.
- **Operator Target**: RTO <= 60 seconds for automated failover, zero data loss.

## 2. Automated CloudNativePG Failover
1. CloudNativePG Operator detects loss of heartbeat from primary instance.
2. Operator evaluates streaming standby replicas with lowest replication lag.
3. Healthy standby is automatically promoted to primary via `pg_ctl promote`.
4. Kubernetes Service `agrin-postgres-cluster-rw` automatically redirects traffic to the new primary.
5. Failed former primary restarts and syncs as standby.

## 3. Manual Operator Failover Procedure
If automatic promotion is blocked due to split-brain prevention:
```bash
# Check cluster status
kubectl cnpg status agrin-postgres-cluster -n agrin-node

# Promote instance 2 manually
kubectl cnpg promote agrin-postgres-cluster 2 -n agrin-node

# Verify application reconnection
kubectl logs -l app.kubernetes.io/component=api -n agrin-node --tail=50
```

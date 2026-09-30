# Operational Runbook: Sovereign Node Ed25519 Key Compromise

## 1. Threat Severity
- **CRITICAL**: If a national node's Ed25519 private key is compromised, an attacker could sign fraudulent federated model weight updates or impersonate the sovereign national node to the BRICS Registry.

## 2. Emergency 3-Step Remediation: Rotate, Revoke, Notify

### Step 1: Revoke Compromised Key at Central Registry
Immediately execute mutual revocation by broadcasting an unregister payload signed with an emergency authority secret:
```bash
curl -X POST https://registry.brics.agri/v1/nodes/revoke \
  -H "X-Node-ID: node-ind-icar-01" \
  -H "X-Emergency-Secret: <EMERGENCY_RECOVERY_TOKEN>" \
  -d '{"reason": "Suspected private key compromise", "compromised_key_sha256": "..."}'
```

### Step 2: Generate New Ed25519 Keypair
On a secure offline air-gapped machine or HSM:
```bash
openssl genpkey -algorithm ed25519 -out node_private_new.key
openssl pkey -in node_private_new.key -pubout -out node_public_new.pub
```
Upload the new private key to HashiCorp Vault / Kubernetes Secret:
```bash
kubectl create secret generic node-ed25519-identity \
  --from-file=node_private.key=node_private_new.key \
  --from-file=node_public.pub=node_public_new.pub \
  --dry-run=client -o yaml | kubectl apply -n agrin-node -f -
```

### Step 3: Re-register with BRICS Registry Working Group
Submit the new `node_public_new.pub` to the Central Registry through official diplomatic / academic channels for inclusion in the verified peer network.
Restart local API and Federation pods:
```bash
kubectl rollout restart deployment/agrin-node-api -n agrin-node
```

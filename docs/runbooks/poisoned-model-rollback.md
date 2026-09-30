# Operational Runbook: Poisoned Federated Model Rollback

## 1. Trigger Scenario
- A federated learning training round was corrupted by malicious weights, adversarial gradient poisoning, or synthetic data manipulation causing model regression (accuracy drop > 10% or inaccurate disease classification).

## 2. Rollback Procedure
1. **Identify Corrupted Model Version**:
   Query the Central Registry model card history:
   ```bash
   curl https://registry.brics.agri/v1/models/wheat-rust-cnn/versions
   ```
2. **Execute Emergency Model Pinning**:
   Pin the local sovereign node to the previous verified cryptographic checkpoint:
   ```bash
   kubectl set env deployment/agrin-node-api PINNED_MODEL_CHECKPOINT="checkpoint_round_04_sha256_e4b1c..." -n agrin-node
   ```
3. **Notify BRICS Registry Working Group**:
   Submit an emergency invalidation ticket to invalidate the round weights on the Flower server coordinator.
4. **Purge Edge Cache**:
   Trigger edge cache invalidation so web and mobile clients re-download the verified ONNX model.

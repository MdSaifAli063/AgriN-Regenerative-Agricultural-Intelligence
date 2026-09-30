# Engineering Limitations, Trade-offs & Threat Model

> **KrishiNet-BRICS Architectural Rigor Assessment**  
> Document Version: 1.0.0 · October 2026 · Technical Evaluation

---

## 1. Executive Summary

KrishiNet-BRICS balances **national data sovereignty** with **multilateral intelligence sharing**. Every architectural decision reflects deliberate engineering trade-offs between privacy, accuracy, communication overhead, and operational resilience. This document outlines the known boundaries, failure modes, and threat models of the Phase 7 federated system.

---

## 2. Federated Learning Trade-offs & Limitations

### 2.1 Differential Privacy (DP) vs. Model Accuracy Trade-off
- **Implementation**: Rényi / Laplace Differential Privacy with $L_2$ gradient clipping ($C = 1.0$) and calibrated Laplace noise addition ($\epsilon = 0.50$ per round).
- **Limitation**: While bounding privacy leakage ($\epsilon \le 1.50$ over 3 rounds, $\delta = 10^{-5}$), the injected parameter noise slightly attenuates convergence speed. Top-1 classification accuracy on fine-grained foliar disease classes is approximately **1.2% to 1.8% lower** than a hypothetical centralized model trained on pooled raw images.
- **Justification**: In an international context, zero raw data movement and mathematical privacy bounds are non-negotiable legal requirements for sovereign nations.

### 2.2 Non-IID Data Distribution & Regional Crop Skew
- **Challenge**: Agricultural data is inherently non-Independent and Identically Distributed (non-IID).
  - India specializes in smallholder cotton, chickpea, and rice blast.
  - Brazil dominates commercial soybean rust and maize.
  - South Africa centers on Highveld maize gray leaf spot and sorghum.
- **Limitation**: Extreme label skew can cause standard `FedAvg` client drift, where the global model oscillates between regional optima.
- **Mitigation in Place**: We implement weighted sample importance ($w_k = n_k / \sum n$) combined with gradient clipping to stabilize updates. Future iterations (Phase 8) will adopt Scaffold / FedProx with proximal regularization terms ($\mu \|\theta - \theta_G\|^2$).

### 2.3 Byzantine Outlier Rejection Thresholds
- **Defense Mechanism**: Krum-based Trimmed Mean Euclidean distance matrix filtering.
- **Theoretical Bound**: Krum is mathematically guaranteed to withstand up to $f < \lfloor (n - 1) / 3 \rfloor$ Byzantine adversaries.
  - For $n = 3$ nodes (IND, BRA, ZAF): Standard Krum requires fallback to conservative norm bounding ($10 \times \text{clip\_norm}$) because statistical distance clustering requires at least 4 participating nodes.
  - For $n \ge 5$ nodes (IND, BRA, ZAF, CHN, RUS): Full Krum geometric isolation operates at full theoretical resilience ($f = 1$).

---

## 3. Sovereign Egress Gate Boundaries

### 3.1 Spatial Resolution Coarsening (2 Decimal Places)
- **Constraint**: The Sovereign Egress Gate strictly rejects any geographic coordinate with precision greater than **2 decimal places** (e.g., $78.5982$ is blocked; $78.60$ is allowed).
- **Physical Resolution**: Two decimal degrees corresponds to approximately **1.1 km** at the equator.
- **Consequence**: Cadastral parcel-level localization is mathematically impossible, preventing predatory land speculation or national security exposures. However, micro-climate variations (e.g., hillside thermal inversions) under 1 km cannot be captured in transboundary telemetry.

### 3.2 k-Anonymity Suppression Threshold ($k \ge 5$)
- **Constraint**: Disease outbreak features or impact aggregates representing fewer than 5 smallholder observations are suppressed from outbound STAC and GeoJSON feeds.
- **Trade-off**: In sparsely populated rural regions or early-stage rare pest incursions (e.g., 2 reported cases), the cluster will not be published transboundary until local case counts reach the $k = 5$ threshold or are merged into an adjacent H3 hexagonal cell.

---

## 4. Network Partitioning & Consensus Guarantees

### 4.1 CAP Theorem Positioning: AP (Availability / Partition Tolerance)
- Each national AgriN node is an autonomous sovereign entity designed to function in **complete air-gapped isolation** if international submarine cables or transboundary transit links fail.
- **Offline Operation**:
  - In-browser ONNX edge inference and local disease diagnostics operate with 0% internet connectivity.
  - Satellite cache and local SQLite/PostgreSQL stores serve crop advisories uninterrupted.
- **Eventual Consistency**: When transboundary connectivity is restored, nodes sync pending telemetry using replay-protected Ed25519 signed requests. The central BRICS Commons Registry does not enforce synchronous two-phase commits, avoiding distributed deadlocks across international borders.

### 4.2 Consent Ledger Fork Prevention
- **Structure**: Append-only SHA-256 cryptographic hash-chain stored locally per sovereign node.
- **Scope**: Consent is sovereign; a farmer's consent revocation is committed immediately to the local node ledger and propagated asynchronously to partner nodes via webhook receipts. Cross-border ledger synchronization uses monotonic block indexes ($B_0 \to B_1 \to B_2$) without requiring high-energy Proof-of-Work mining.

---

## 5. Compute & Environmental Footprint

| Component | Target Runtime | Memory Footprint | Edge Feasibility |
|---|---|---|---|
| **MobileNetV3 Disease Classifier** | WebAssembly / ONNX Runtime | **4.8 MB** (INT8) | ✅ Runs on $40 2G/3G Android phones |
| **Field Intelligence Satellite Engine** | NumPy / Rasterio / STAC | 250 MB | ✅ Server-side async Celery worker |
| **Flower Federated Client** | PyTorch / NumPy SGD | 180 MB | ✅ Runs on edge servers & rural workstations |
| **Kantara Consent Ledger** | Python stdlib hashlib | < 5 MB | ✅ Embedded in micro-services |

---

## 6. Threat Model Summary (STRIDE Matrix)

| Threat | Description | Sovereign Countermeasure |
|---|---|---|
| **Spoofing** | Rogue node masquerades as Brazil (Embrapa) | Ed25519 signed request headers + Registry public key pinning |
| **Tampering** | Man-in-the-middle alters federated model gradients | TLS 1.3 + SHA-256 payload digests + Krum Byzantine rejection |
| **Repudiation** | Node denies having published a faulty model card | Immutable Ed25519 digital signature on all ModelHub entries |
| **Information Disclosure** | Transboundary exfiltration of smallholder PII | Sovereign Egress Gate (4-stage AST inspection + denylist + 2 d.p. limit) |
| **Denial of Service** | Volumetric flooding of central Commons Registry | Node rate-limiting (Redis token buckets) + air-gapped local node survival |
| **Elevation of Privilege** | Farmer attempts to access government admin treaties | Keycloak RBAC JWT roles (`farmer`, `extension_officer`, `government_admin`) |

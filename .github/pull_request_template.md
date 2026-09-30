## Summary of Changes
<!-- Provide a brief, high-level summary of what this PR does and why it was introduced. -->

## Linked Issues
<!-- e.g. Fixes #123, Closes #456 -->

---

## 🛡️ Responsible AI & Data Sovereignty Checklist
*All PRs touching agronomic models, farmer telemetry, consent, or messaging MUST satisfy these criteria:*

- [ ] **Farmer Consent & Sovereignty**:
  - [ ] No telemetry or soil data is egressed without verifying `has_consent` or checking the immutable consent ledger.
  - [ ] Any newly created data paths support the "Delete My Data" (Right to be Forgotten) erasure procedure.
- [ ] **Telemetry & Log Privacy**:
  - [ ] Zero unhashed phone numbers, high-precision GPS coordinates, or Bearer tokens are emitted to logs.
  - [ ] Structured logging uses `JSONFormatter` and `PrivacyScrubber`.
- [ ] **Agronomic Safety & Bias Control**:
  - [ ] Recommendations prioritize organic, biological, and non-chemical practices before chemical pesticides.
  - [ ] Chemical dosage limits adhere to national agronomic extensions; no synthetic or unvalidated dosages.
  - [ ] Escalation flag triggers when ensemble confidence drops below safety thresholds (`confidence < 0.65`).
- [ ] **Accessibility & Offline Support**:
  - [ ] Messaging changes support both WhatsApp rich cards and low-cost GSM-7 SMS pagination.
  - [ ] Numeric navigation (`0=Back`, `9=Menu`) verified for feature-phone compatibility.
  - [ ] Multilingual catalog keys validated across all 12 supported BRICS/African locales.
- [ ] **Quality Gates**:
  - [ ] Backend tests maintain >= 80% line coverage (`pytest --cov-fail-under=80`).
  - [ ] Frontend tests maintain >= 70% coverage.
  - [ ] Strict type checking passes (`mypy --strict`, `tsc --noEmit`).

---

## Verification & Screenshots
<!-- Attach test execution logs, CLI simulator replays, or UI screenshots confirming functionality. -->

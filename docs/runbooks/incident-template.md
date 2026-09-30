# Post-Mortem & Incident Report Template

## Incident Overview
- **Incident ID**: INC-YYYYMMDD-01
- **Severity**: [Sev-1 / Sev-2 / Sev-3]
- **Services Impacted**: [e.g. Backend API, Celery Workers, Twilio Gateway, Registry]
- **Duration**: [e.g. 42 minutes]
- **Incident Commander**: [Name / Role]
- **Date & Time**: YYYY-MM-DD HH:MM UTC

---

## Executive Summary
Brief non-technical summary of what occurred, why, and the impact on smallholder farmers and extension officers.

---

## Timeline of Events (UTC)
- **HH:MM** - Anomaly detected via Prometheus Alert `...`
- **HH:MM** - Incident triage began; circuit breaker verified.
- **HH:MM** - Mitigation deployed (e.g. fallback to rules engine / simulator).
- **HH:MM** - Primary root cause resolved.
- **HH:MM** - Full service restored; smoke test verified green.

---

## Root Cause Analysis (5 Whys)
1. Why did the service fail?
2. Why?
3. Why?
4. Why?
5. Why?

---

## Farmer Data Sovereignty & Privacy Impact
- Were any farmer coordinates, phone numbers, or unencrypted assets exposed? [YES / NO]
- Was data sovereignty maintained? [YES / NO]
- Did the immutable consent ledger record all actions? [YES / NO]

---

## Action Items & Preventative Measures
| Action Item | Owner | Target Date | Status |
| :--- | :--- | :--- | :--- |
| Add integration test for outage scenario | @eng-lead | YYYY-MM-DD | Open |
| Tune Prometheus alert threshold | @sre-lead | YYYY-MM-DD | Open |

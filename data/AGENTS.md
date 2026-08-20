# AGENTS.md — data/

## Ownership
Versioned, offline-first product data fixtures owned by their defining subsystem.

## Purpose
Holds `ontology.yaml`, Crucible's single YAML catalog of thirty attack vectors.

## What This Controls
Catalog content consumed by `load_ontology()`. Wrong names, status, rail, telemetry requirement, or mutation parameters make downstream Identify, simulation, evaluation, and loop behavior inconsistent with PRD.

## Connections
- Depends on: exact vector list in [`../docs/PRD.md`](../docs/PRD.md).
- Depended on by: [`../src/crucible/ontology/schema.py`](../src/crucible/ontology/schema.py) and [`../tests/test_ontology.py`](../tests/test_ontology.py).
- External systems touched: none.

## Current State
Working CRU-01 source data: eight canonical `simulated` vectors and twenty-two `playbook` vectors, all schema-valid. Simulated vector IDs and snake_case families match refreshed PRD adapter and holdout rules; playbook families are restricted to the four refreshed categories.

## Decision Log

### 2026-08-20 — Refreshed canonical crew mappings
- **Change**: Replaced legacy simulated IDs and display-name families with PRD-defined IDs and families; normalized playbook families to `phishing`, `synthetic_id`, `adversarial_ml`, or `refund_abuse`.
- **Reasoning**: Data must agree exactly with adapter registry, zero-day holdout masking, and mutation eligibility.
- **Rejected alternative(s)**: Retaining human-readable legacy family names — they would not match `agentic_checkout` and `remittance_injection` policy rules.
- **Task/session**: Full refreshed-spec TDD implementation.

### 2026-08-20 — Added single source ontology catalog
- **Change**: Added `ontology.yaml` with all PRD-listed vector families, rails, statuses, telemetry requirements, and mutation parameters.
- **Reasoning**: PRD requires a YAML source rather than executable constants; simulated vectors carry mutation parameters for future crews while playbook-only vectors retain an explicit empty list. PRD provides no playbook-only rail or telemetry mapping, so these values are provisional schema-complete assignments pending product review.
- **Rejected alternative(s)**: Omitting mutation parameters on playbook vectors — violates catalog schema requirement. Adding unlisted crews — root rules lock simulated crew count at eight.
- **Task/session**: Project initialization and TDD CRU-01 delivery.

## Known Gotchas
Do not replace vector IDs or families with synonyms: zero-day and mutation rules use exact values. Do not add a ninth simulated vector before feature freeze.

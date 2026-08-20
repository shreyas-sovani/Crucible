# AGENTS.md — src/crucible/ontology/

## Ownership
Attack Ontology subsystem: source-of-truth validation and loading for Crucible's thirty attack vectors.

## Purpose
Turns `../../../data/ontology.yaml` into immutable, schema-valid `Vector` records through public `load_ontology()`.

## What This Controls
Every consumer's vector names, dual rail, simulation/playbook classification, GenAI telemetry requirements, and mutation options. Invalid or incomplete catalog data corrupts Identify view, crew selection, holdouts, and later feedback-loop configuration.

## Connections
- Depends on: [`../../../data/ontology.yaml`](../../../data/ontology.yaml); `pydantic` and `PyYAML` declared in [`../../../pyproject.toml`](../../../pyproject.toml).
- Depended on by: [`../../../tests/test_ontology.py`](../../../tests/test_ontology.py); future simulator crews, API, and UI data surface.
- External systems touched: none.

## Current State
Working CRU-01 implementation. `Vector` forbids unknown fields and freezes valid records. `load_ontology()` validates YAML each call and returns all thirty refreshed-catalog vectors, including canonical simulated crew IDs and families.

## Decision Log

### 2026-08-20 — Aligned catalog with refreshed crew identities
- **Change**: Expanded vector ID validation to canonical underscore/uppercase IDs and updated simulated IDs/families to `V-CIP_Mule` through `Voice_Clone_Exec`; grouped playbook-only families into refreshed PRD categories.
- **Reasoning**: Refreshed PRD supersedes previous human-readable family labels and supplies exact adapter identities plus zero-day family names.
- **Rejected alternative(s)**: Maintaining old display-name families — detector holdouts and crew lookup would no longer agree. A duplicate package catalog — Hatch now force-includes the same `data/ontology.yaml` in the wheel.
- **Task/session**: Full refreshed-spec TDD implementation.

### 2026-08-20 — Implemented validated YAML ontology loader
- **Change**: Added `schema.py` with immutable Pydantic `Vector` and public `load_ontology(path=None)`; default path resolves repository `data/ontology.yaml`.
- **Reasoning**: YAML is PRD-required source of truth; Pydantic catches malformed fields at module boundary before simulator or API consumes them.
- **Rejected alternative(s)**: Python hard-coded catalog — would violate YAML catalog requirement. Returning raw dictionaries — would defer schema failures into downstream modules. Separate duplicate package data copy — would create two catalog sources.
- **Task/session**: Project initialization and TDD CRU-01 delivery.

## Known Gotchas
Preserve `data/ontology.yaml` as sole catalog source. The loader uses repository data in checkout and packaged `crucible/data/ontology.yaml` only when installed from a wheel. Do not change simulated IDs or snake_case families: crew lookup and zero-day masking depend on them.

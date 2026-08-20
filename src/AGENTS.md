# AGENTS.md — src/

## Ownership
Crucible backend Python package boundary.

## Purpose
Contains importable runtime code for ontology, future Event Envelope simulation, features, detector, loop, and API modules.

## What This Controls
Package layout and build discovery. Wrong files or imports here prevent `crucible` from loading and block every backend module and test.

## Connections
- Depends on: root [`../pyproject.toml`](../pyproject.toml) for Python dependencies and Hatch package discovery.
- Depended on by: [`../tests/`](../tests/); future backend entry points and API modules.
- External systems touched: none; project is offline-first.

## Current State
Working backend package. All refreshed-PRD backend child packages exist and are covered by public-interface pytest tests.

## Decision Log

### 2026-08-20 — Completed refreshed-spec backend package
- **Change**: Added `crucible` child packages for models, simulator, features, detector, evaluation, loop, and API.
- **Reasoning**: The PRD tree keeps each responsibility deep and independently testable while sharing only typed Event and CrewConfig boundaries.
- **Rejected alternative(s)**: One orchestration module or pass-through wrappers — those would collapse simulator, model, and policy seams.
- **Task/session**: Full refreshed-spec TDD implementation.

### 2026-08-20 — Initialized source package for CRU-01
- **Change**: Added `crucible/__init__.py` and source-layout build configuration in `../pyproject.toml`.
- **Reasoning**: Hatch requires an explicit package target before `uv run pytest` can build this empty-to-new source layout.
- **Rejected alternative(s)**: Flat root-level Python modules — backlog requires `src/crucible/...` paths. Deferring packaging configuration — tests could not import project code.
- **Task/session**: Project initialization and TDD CRU-01 delivery.

## Known Gotchas
Keep subsystem logic below `crucible/`; do not put simulator, detector, or API code in this package root.

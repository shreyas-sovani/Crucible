# AGENTS.md — src/crucible/

## Ownership
Crucible's core Python namespace and subsystem boundary.

## Purpose
Provides stable `crucible.*` imports while child packages isolate ontology, simulator, crew, feature, detector, loop, and API responsibilities.

## What This Controls
Namespace integrity. Changing package-level exports or crossing subsystem boundaries can couple modules that must remain independently testable.

## Connections
- Depends on: [`../../pyproject.toml`](../../pyproject.toml) for runtime dependencies and source packaging.
- Depended on by: [`../../tests/test_ontology.py`](../../tests/test_ontology.py) and future backend modules.
- External systems touched: none.

## Current State
Working namespace containing isolated `api`, `detector`, `evaluation`, `features`, `loop`, `models`, `ontology`, and `simulator` packages. Package root remains intentionally behavior-free.

## Decision Log

### 2026-08-20 — Filled complete refreshed-PRD namespace
- **Change**: Added all eight required subsystem packages below the existing namespace.
- **Reasoning**: Each PRD concern owns its state and interface; dependencies flow through Event frames and CrewConfig rather than root orchestration.
- **Rejected alternative(s)**: Moving cross-subsystem logic into `__init__.py` — would violate deep module boundaries.
- **Task/session**: Full refreshed-spec TDD implementation.

### 2026-08-20 — Created minimal namespace package
- **Change**: Added `__init__.py` with package documentation only.
- **Reasoning**: Keep package root free of orchestration so deep modules remain isolated as required by PRD.
- **Rejected alternative(s)**: Re-exporting loaders or creating a global application object — those would make later modules depend on a shallow central wrapper.
- **Task/session**: Project initialization and TDD CRU-01 delivery.

## Known Gotchas
Do not add pass-through wrappers here; module interfaces belong in their owning child package.

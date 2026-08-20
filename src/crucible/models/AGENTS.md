# AGENTS.md — src/crucible/models/

## Ownership
Typed Event Envelope and CrewConfig contract boundary.

## Purpose
Validates card and UPI payment records, optional GenAI telemetry, and bounded simulated crew configuration before any simulator or policy code uses them.

## What This Controls
Raw PAN exposure, rail/payload mixing, invalid event IDs or UTC timestamps, and invalid mutation ranges are rejected here rather than leaking into simulation or APIs.

## Connections
- Depends on: `pydantic` in [`../../../pyproject.toml`](../../../pyproject.toml); canonical fields in [`../../../CONTEXT.md`](../../../CONTEXT.md).
- Depended on by: `simulator/crews.py`, `simulator/world.py`, `loop/mutator.py`, and `api/main.py`.
- External systems touched: none.

## Current State
Working. `Event` enforces UUIDv4, UTC, exact rail payload selection, and optional bounded telemetry. `CardPayload` rejects 13–19 digit raw PANs. `CrewConfig` freezes ordered non-negative bounds.

## Decision Log

### 2026-08-20 — Implemented unified Event and CrewConfig boundaries
- **Change**: Added `event.py` and `config.py` plus package exports.
- **Reasoning**: Pydantic protects the shared interface once; all modules can consume validated immutable contracts.
- **Rejected alternative(s)**: Untyped dictionaries or split card/UPI top-level event streams — both would duplicate validation and defeat unified Envelope requirements.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
`label=None` is valid only for inference; do not use it as a feature. Event timestamps must be UTC, not merely timezone-aware.

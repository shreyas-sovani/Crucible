# AGENTS.md — src/crucible/api/

## Ownership
Stateless offline Lab HTTP boundary.

## Purpose
Serves validated ontology, complete offline closed-Cycle artifacts, and real Cycle-stage stream events under `/api`, then serves built React assets at `/` when `frontend/dist` exists.

## What This Controls
UI/backend contract. Wrong paths, request validation, or mount order breaks visualizer data or shadows API endpoints.

## Connections
- Depends on: `ontology/schema.py`, `simulator/world.py`, `simulator/topology.py`, `models/config.py`, FastAPI, and optional [`../../../frontend/dist`](../../../frontend/dist).
- Depended on by: frontend `src/App.jsx` and `tests/test_api.py`.
- External systems touched: none.

## Current State
Working. `GET /api/ontology` returns Vector objects; `POST /api/cycle` remains the completed Cycle contract. Additive `POST /api/cycle/stream` emits four actual stage events, then the exact same Cycle artifact as a final SSE event. `CycleSummary` now also carries fidelity-gate verdicts, IST business-hour share, delayed card-label counts, per-family `FamilyEfficacySummary` rows, and an `EvidenceSummary` of token-only frozen-Test catches/misses. Static mount is conditional so backend tests work before UI build.

## Decision Log

### 2026-08-20 — Serialized fidelity, efficacy, and evidence artifacts (CRU-14/15/18/19)
- **Change**: Extended `GenerationSummary` (four KS p-values incl. `None` for sub-50 samples, IST share/pass, gate count, `fidelity_pass`), `DetectionSummary` (delayed card-label count/share, `family_efficacy`), and added `FamilyEfficacySummary`, `EvidenceEventSummary`, `EvidenceSummary` to `_cycle_summary()`. `CycleRequest` bounds already permit the spec scale (`n_days` ≤ 90, `num_users` ≤ 10,000).
- **Reasoning**: The Lab UI is HTTP-only; every judge-facing artifact (gate verdicts, zero-day per-family table, concrete attack samples, spec-scale presets) must cross this boundary as typed models.
- **Rejected alternative(s)**: Flattening evidence into detection metrics — hides the Identify→Simulate narrative judges inspect. Loosening request bounds — spec constants are the documented maximum.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Streamed actual Cycle boundaries
- **Change**: Added `POST /api/cycle/stream`, SSE packet serialization, and shared `_cycle_summary()` in `main.py`; retained `POST /api/cycle` unchanged.
- **Reasoning**: The browser needs work-boundary messages while the synchronous offline Cycle runs. A queue plus worker thread flushes callback events as they happen and returns the established typed artifact only after completion.
- **Rejected alternative(s)**: Client timers or fabricated percentages — not backend work. Converting the existing JSON endpoint to SSE — breaks its response model and current consumers. WebSockets — UI only needs one HTTP request stream.
- **Task/session**: Make full offline Cycle visibly unfold from real work.

### 2026-08-20 — Exposed audit-grade detector evidence
- **Change**: Extended `DetectionSummary` with label-available counts and validation/Test FPR/recall at the selected operating point.
- **Reasoning**: HTTP is the Lab boundary; judges and UI consumers need to distinguish the validation-selected policy from a frozen-Test 1%-FPR score metric.
- **Rejected alternative(s)**: Returning a threshold and one recall number only — cannot show whether the claimed FPR budget or delayed-label training rule was real.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Replaced count-only Cycle response with real artifacts
- **Change**: `main.py` now calls `loop.orchestrator.run_closed_loop()` and serializes nested Generation, Detection, and Mutation response models.
- **Reasoning**: API endpoint must represent the actual lab workflow rather than only world generation; typed artifacts let UI display every stage without importing backend code.
- **Rejected alternative(s)**: Client-side calculations or placeholder metric fields — violate HTTP-only boundary and create unverified judge evidence.
- **Task/session**: Diagnose and complete no-op Run Offline Cycle.

### 2026-08-20 — Implemented Lab REST surface and static mount
- **Change**: Added FastAPI `app`, `CycleRequest`, `/api/ontology`, `/api/cycle`, and conditional root static mount.
- **Reasoning**: UI uses only HTTP and can run offline; mount follows API routes so `/api/*` retains precedence.
- **Rejected alternative(s)**: UI importing Python modules — violates Lab surface rule. Unconditional mount — fails when Vite build does not exist in test/development checkout.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
Rebuild frontend after source changes or `/` serves stale assets. Keep `CycleRequest.num_users` bounded to protect local demo runtime. Omit `crews` to activate all eight canonical default configs; passing a list overrides them. `test_fpr_at_operating_point` may differ from 1% because threshold is selected on Validation; use `recall_at_1pct_fpr` only for frozen-Test ranking efficacy. `cycle/stream` sends `stage`, then exactly one `result` or `error`; never derive stage data in the browser.

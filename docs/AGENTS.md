# AGENTS.md — docs/

## Ownership
Product and program documentation for Crucible (not runtime code). Canonical specs for any coding agent.

## Purpose
Holds the PRD and the in-repo backlog. Agents read these instead of reconstructing product decisions from chat.

## What This Controls
Wrong or stale docs here cause agents to implement the wrong rails, eval protocol, crew list, or work order. `BACKLOG.md` is the only task queue (no Linear/Jira).

## Connections
- Depends on: [`../CONTEXT.md`](../CONTEXT.md) (glossary the PRD assumes)
- Depended on by: root [`../AGENTS.md`](../AGENTS.md); all future application modules
- External systems touched: none

## Current State
Working canonical implementation documentation. Refreshed `CONTEXT.md` supplies constants, schemas, and distributions; `PRD.md` supplies module invariants. `BACKLOG.md` records CRU-01–CRU-20, including real HTTP Cycle-stage streaming, a retained completed Lab trace, honest-fidelity gates with verdicts, delayed-label and per-family zero-day efficacy evidence, token-only event samples, and spec-scale (90d × 10,000 users) verified realism, all `done` with test evidence.

## Decision Log

### 2026-08-20 — Added spec-scale and judge-evidence tickets
- **Change**: Added CRU-14–CRU-20 rows covering per-family zero-day efficacy, fidelity gate verdicts, per-user entities, vectorized causal windows, evidence samples, Lab scale controls, and spec-scale realism (80% IST window, truncated normals, world-scaled fraud, imbalance-aware detector).
- **Reasoning**: Technical-gap audit against `CONTEXT.md`/`PRD.md` found the zero-day table, fidelity verdicts, delayed-label counts, and spec constants were claimed but not measurable or reachable; each fix needed an explicit ticket and test evidence per the execution rule.
- **Rejected alternative(s)**: Folding everything into one "polish" ticket — loses test-per-claim traceability judges can audit.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Added retained Cycle-trace ticket
- **Change**: Added and completed CRU-13 for keeping the four received Cycle-stage events visible after the final artifact renders.
- **Reasoning**: A local Cycle can finish in less than a second; unmounting the trace when the request resolves hides real backend work before judges can inspect it.
- **Rejected alternative(s)**: A minimum-duration timer or replayed client animation — delay or fabricate the observation instead of retaining the actual event record.
- **Task/session**: Fix blink-and-disappear Lab buffers.

### 2026-08-20 — Added real-time Cycle trace ticket
- **Change**: Added and completed CRU-12 for an additive Cycle stage stream and frontend rendering test.
- **Reasoning**: The completed Cycle artifact was real but arrived as one response, leaving judges unable to see the closed loop doing work. The ticket requires actual backend boundaries, not timed client animation.
- **Rejected alternative(s)**: Simulated progress percentages or a UI-only stepper — fabricate process. Replacing `POST /api/cycle` — breaks the established Lab contract.
- **Task/session**: Make full offline Cycle visibly unfold from real work.

### 2026-08-20 — Corrected closed-loop honesty gaps
- **Change**: Added CRU-11 and evidence for distinct crew behaviour, legitimate-only fidelity KS checks, 45-day card-label availability, empirical 1% FPR reporting, missed-row SHAP, and Train-window-only retraining.
- **Reasoning**: CRU-10 made Cycle executable but did not prove its generated attacks, delayed labels, operating point, or resimulation followed `CONTEXT.md`/`PRD.md` exactly.
- **Rejected alternative(s)**: Hiding a zero recall, forcing a positive mutation, or treating delayed fraud as legitimate — each would make judge-facing evidence look better while invalidating the experiment.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Added executable Cycle ticket
- **Change**: Added CRU-10 for real orchestration and judge-visible evidence, with HTTP and UI regression coverage.
- **Reasoning**: Previous `/api/cycle` generated a frame but stopped before features, detector, policy, mutation, or visual evidence. A 200 response was not a completed closed loop.
- **Rejected alternative(s)**: Returning fabricated metrics or a mock mutation — violates simulation-only honesty and user request. Leaving orchestration implicit in the UI — client must consume Lab HTTP only.
- **Task/session**: Diagnose and complete no-op Run Offline Cycle.

### 2026-08-20 — Restored refreshed-PRD ticket queue
- **Change**: Replaced malformed `BACKLOG.md` duplicate-PRD content with CRU-01–CRU-09 dependency order, status, and test evidence.
- **Reasoning**: User refreshed the canonical documents and requested full implementation. The file named backlog contained no tickets, so the queue now records exact PRD module order without importing stale requirements.
- **Rejected alternative(s)**: Retaining duplicate PRD as a task queue — it offered no status or execution order. Reusing prior backlog entries — they described superseded schemas and policy bands.
- **Task/session**: Full refreshed-spec TDD implementation.

### 2026-08-20 — CRU-01 completion and CRU-02 source block recorded
- **Change**: Updated `BACKLOG.md` with CRU-01 `done`, CRU-02 `needs-triage` block, and later-ticket state; updated this handoff with exact source discrepancy.
- **Reasoning**: CRU-01's required catalog test passes. CRU-02 explicitly requires a schema from `CONTEXT.md`, but its present contents are a byte-for-byte PRD duplicate, so creating payload types would invent canonical terms and behavior.
- **Rejected alternative(s)**: Marking CRU-02 ready by extrapolating fields from `PRD.md` — root rules prohibit re-deriving the glossary and schemas. Starting downstream simulation, detector, API, or UI tickets — calendar dependency rule prevents it.
- **Task/session**: Project initialization and TDD CRU-01 delivery.

### 2026-08-19 — PRD and backlog landed
- **Change**: Added `PRD.md` (full product + modules + tests + out of scope) and `BACKLOG.md` (CRU-01…CRU-16).
- **Reasoning**: No issue tracker is connected; agents need a single spec and a calendar-ordered queue. Glossary stays in `CONTEXT.md` so this directory is not the term dictionary.
- **Rejected alternative(s)**: Publishing to Linear/Jira — no backend in this workspace. Putting the glossary inside the PRD only — agents would drift on synonyms; `CONTEXT.md` is the term seam.
- **Task/session**: to-prd after thesis, dual-rail, and eval protocol were locked.

## Known Gotchas
- Implement against `PRD.md` + `CONTEXT.md`, not against canvases or chat summaries.
- Do not start CRU-14 (UI) before CRU-01–CRU-03 exist; backlog header states this.
- Dual rail, eight crews, LightGBM, no trained GNN, no LangGraph are locked in the PRD — do not reopen in a coding session without an ADR.

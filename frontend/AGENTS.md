# AGENTS.md — frontend/

## Ownership
Crucible Lab browser visualizer and its Vite build configuration.

## Purpose
Builds a stateless React interface that fetches validated ontology, streams real Cycle boundaries, and renders final offline Cycle evidence only through FastAPI `/api` routes.

## What This Controls
Demo usability and browser/API compatibility. Wrong proxy or route names leave the Lab blank; committing generated dependencies bloats the repository.

## Connections
- Depends on: `package.json`, Vite, React Query, and backend `../src/crucible/api/main.py`.
- Depended on by: FastAPI static mount after `npm run build` creates `dist/`.
- External systems touched: local `/api` only; no direct payment or third-party API calls.

## Current State
Working Vite/React application. `npm test` verifies ontology, actual streamed Cycle stages, retained completed trace, and final evidence rendering; `npm run build` emits static assets served by FastAPI. The progressive trace uses backend SSE events and does not synthesize progress or metrics; it remains above the final artifact until the next Cycle starts.

## Decision Log

### 2026-08-20 — Retained completed Cycle trace
- **Change**: Updated `src/App.jsx`, `src/App.test.jsx`, and `src/styles.css` so the received Identify → Simulate → Detect → Mutate trace remains visible above final evidence after the stream delivers its artifact.
- **Reasoning**: The backend work is genuine but fast. Preserving the received event record gives judges time to inspect the actual loop without changing the Cycle contract or delaying evidence.
- **Rejected alternative(s)**: A fake minimum dwell or a timer-driven replay — neither represents backend timing. Dropping evidence behind a separate review screen — adds navigation to the judge path.
- **Task/session**: Fix blink-and-disappear Lab buffers.

### 2026-08-20 — Made Cycle visible while it runs
- **Change**: Updated `src/App.jsx`/`styles.css` to consume `POST /api/cycle/stream` and render an instrument-style live trace; existing final evidence still uses only final Cycle artifact data.
- **Reasoning**: Judges need causal visibility before completion. The copper scan motion signifies an open backend event stream, while stage state changes only when an actual server event arrives.
- **Rejected alternative(s)**: A timer-driven loader — would fake work. Replacing final evidence with interim numbers — no partial metrics are exposed by the backend.
- **Task/session**: Make full offline Cycle visibly unfold from real work.

### 2026-08-20 — Reverified static Lab against honest Cycle response
- **Change**: Ran the existing UI suite and production build after backend Cycle gained label-availability and operating-point evidence; no visual or source change was made.
- **Reasoning**: Task scope is technical correctness, while the existing evidence tape already calls the real HTTP Cycle endpoint. API response-model expansion is backwards-compatible with it.
- **Rejected alternative(s)**: Adding new UI chrome solely to repeat backend metrics — user explicitly prioritized deep modules over presentation work.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Turned Cycle response into judge-visible evidence
- **Change**: Reworked `src/App.jsx` into generation, frozen-Test detection, and mutation evidence tape populated from nested `/api/cycle` artifacts.
- **Reasoning**: Judges need to see actual causal process, decisions, SHAP, loss, zero-day masking, and mutation outcome—not a 200 response/count pair.
- **Rejected alternative(s)**: Decorative fake charts — would misrepresent model behavior. A status toast — does not explain what happened in the lab.
- **Task/session**: Diagnose and complete no-op Run Offline Cycle.

### 2026-08-20 — Built offline Lab visualizer
- **Change**: Added Vite config, React Query app, UI test, and production build scripts.
- **Reasoning**: Slate/copper ledger visual language makes the closed Identify→Simulate→Detect→Mutate sequence tangible while maintaining dense analyst-readable data.
- **Rejected alternative(s)**: Direct backend imports or mocked vector data — violate API-only and source-of-truth rules. A generic dashboard grid — obscures the closed-loop sequence.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
Run `npm install` after changing dependencies; `node_modules/` and `dist/` are ignored. Vite development server proxies `/api` to port 8000. Default Cycle seed `1` can honestly return no eligible in-sample miss; do not force a mutation merely to show an outcome. Do not use `EventSource`: it cannot POST the seeded Cycle request; use streamed `fetch` and retain incomplete SSE packet buffering.

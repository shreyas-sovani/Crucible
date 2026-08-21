# AGENTS.md — frontend/src/

## Ownership
React application composition, visual system, and browser behavior tests.

## Purpose
Renders ontology ledger, live Cycle-stage trace, and full Cycle evidence; `App.jsx` is the only API consumer and `App.test.jsx` verifies streamed stage behavior plus visible final artifacts.

## What This Controls
Displayed terms and interactive offline cycle behavior. Incorrect copy, stream buffering, or client data flow can drift from Context vocabulary, make real work look fake, or bypass Lab HTTP surface.

## Connections
- Depends on: React Query, `../vite.config.js`, and `/api/ontology`, `/api/cycle/stream` supplied by `../../src/crucible/api/main.py`.
- Depended on by: `../index.html` and Vite production build.
- External systems touched: local Lab API only.

## Current State
Working. `App.jsx` fetches vectors, POSTs the Cycle stream with user-selected seed and world-scale preset (`SCALE_PRESETS`: demo 3d × 80, GFF 30d × 1,500, spec 90d × 10,000), buffers SSE packets, and yields each received stage through browser paints before consuming the next. Once the returned artifact arrives, it retains the four actual stage events above the evidence tape until the next Cycle clears them. The evidence tape renders generation metrics with fidelity gate chips (four KS gates + IST hours + overall verdict), frozen-Test detection metrics with delayed-label counts, SHAP, loss, a per-family efficacy table with in-sample/zero-day aggregates, concrete top-catch and APPROVE-miss event tables, and the mutation result. `styles.css` defines responsive slate/copper palette, visible focus, and reduced-motion-safe scan motion.

## Decision Log

### 2026-08-21 — Product-UX rework: analyst-first framing, progressive disclosure (CRU-22 follow-up)
- **Change**: Removed the "what judges check for" implementation-claims panel entirely. `FirstRunGuide` → `GetStarted` (three plain workflow steps, no evaluation claims). `CycleEvidence` → `AssessmentOutcome`: leads with an outcome strip (attacks caught, approved fraud + $ loss, legitimate-decline rate, volume), then transaction review tables ("Highest-risk declined payments" / "Fraudulent payments approved — review these first") whose per-row reasoning is a `<details>` drill-down pairing plain-language signal labels (`FEATURE_LABELS`, e.g. `prior_tx_count` → "Account history length") with the raw feature code and signed value. Fidelity chips, operating-point/label-lag notes, and metric definitions moved into `<details className="tech-detail">` blocks ("Traffic realism checks", "Model detail"). Efficacy table reframed as "Results by attack type" with "Seen/Never seen in training". Copy throughout targets a payment risk analyst: "Run assessment", "Scenario seed", "Traffic volume", "Assessment history".
- **Reasoning**: User directive — the Lab must read as a real product, not a hackathon dashboard; judges discover capability through normal interaction, and technical evidence stays available behind progressive disclosure instead of lead marketing copy.
- **Rejected alternative(s)**: Keeping evaluator language ("fidelity gates", "zero-day rows", "TreeSHAP") in primary copy — implementation detail posing as product value. Hiding technical evidence entirely — deep-inspection value would be lost; disclosure keeps it one click away.
- **Task/session**: Product-UX rework after CRU-22 feedback.

### 2026-08-21 — Run ledger, first-run guide, guard-aware errors, per-event why (CRU-22)
- **Change**: `App.jsx` adds a client-side run history (last 8 runs with artifact + stage trace, click-to-revisit, per-run Δ frozen-Test PR-AUC vs the run before), a `FirstRunGuide` panel shown until the first successful run, `ErrorPanel` mapping HTTP 409/429 from the Cycle guard to plain-language guidance, per-stage `+Xs server-side` chips from SSE `elapsed_ms`, signed `top_shap` chips in the catch/miss tables, and rail/mode filter chips on the ontology ledger. `requestCycleStream` now parses rejection JSON and attaches `error.status`. `test-setup.js` gained RTL `afterEach(cleanup)`.
- **Reasoning**: Judges had no way to explore seeds (each run erased the last), no self-guided onboarding, no sense of progress on long runs, and 409/429 rendered as raw status strings. Every addition renders only real backend artifacts; the only client-side derivation is arithmetic over two returned PR-AUC values, labeled as such.
- **Rejected alternative(s)**: localStorage persistence — breaks the stateless-Lab rule and adds no demo value within one judging session. Timer-based progress — fabricates work. Disabling the run button after errors — protection must stay server-side (CRU-21).
- **Task/session**: Judge-interaction UX pass.

### 2026-08-20 — Cycle controls, fidelity gates, efficacy table, event evidence (CRU-19)
- **Change**: `App.jsx` adds seed input + scale presets feeding the real POST body, `GateChip` fidelity chips, `FamilyEfficacyTable` with zero-day/in-sample aggregate rows, and `EventEvidence` catch/miss tables; `App.test.jsx` asserts the posted body and the new renderings from the streamed artifact.
- **Reasoning**: Spec constants (`n_days = 90`, `num_users = 10,000`) were unreachable from the Lab, and gate verdicts, per-family zero-day efficacy, and concrete attack samples are the artifacts judges cross-check against CONTEXT/PRD. All values come from the backend artifact; the UI adds no derived statistics beyond aggregate sums shown in the table footer.
- **Rejected alternative(s)**: Free-form day/user inputs — invites invalid requests the API would reject mid-demo. Client-side KS recompute — duplicates backend truth.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Keep completed backend trace on screen
- **Change**: `App.jsx` now renders `LiveCycleTrace` while pending and after a successful result when received stage events exist; the trace switches to a completed label, all stages are complete, and scan motion is subdued. `App.test.jsx` asserts this post-result record remains visible.
- **Reasoning**: The final artifact changes React Query pending state immediately, which previously unmounted the only view of real stream packets. Keeping those packets alongside the artifact fixes visibility without changing or delaying backend work.
- **Rejected alternative(s)**: Extending `afterPaint()` with arbitrary waits — still makes the trace disappear and misstates latency. Reconstructing stages from final metrics — would create a synthetic trace.
- **Task/session**: Fix blink-and-disappear Lab buffers.

### 2026-08-20 — Added buffered real-time Cycle trace
- **Change**: Added `requestCycleStream()`, `LiveCycleTrace`, stage-aware track state, two-paint stage rendering, and CSS scan/trace styles; rewrote `App.test.jsx` around incrementally delivered SSE packets.
- **Reasoning**: `fetch` reader buffering handles partial network chunks while two browser paints prevent a fast, coalesced stream from visually skipping real stages. Every visible status still comes directly from backend `stage` data; final `result` remains the sole source for all metrics.
- **Rejected alternative(s)**: Calling `/api/cycle` then animating stages locally — visual fiction. Rendering incomplete model numbers — backend intentionally returns artifact only after frozen-Test work completes.
- **Task/session**: Make full offline Cycle visibly unfold from real work.

### 2026-08-20 — Added actual Cycle evidence tape
- **Change**: Added `CycleEvidence`, nested metric panels, SHAP magnitude bars, truthful mutation state, and click regression test.
- **Reasoning**: Layout follows causal lab sequence so every displayed number maps to an API artifact and Test-freeze boundary remains explicit.
- **Rejected alternative(s)**: A generic card dashboard — obscures relationships. Rendering a mutation as success when Δ is negative or no miss exists — contradicts honest evaluation.
- **Task/session**: Diagnose and complete no-op Run Offline Cycle.

### 2026-08-20 — Added API-only cycle ledger
- **Change**: Added `App.jsx`, entry point, styles, test setup, and React Testing Library test.
- **Reasoning**: One focused page lets judges inspect source-of-truth vectors then generate an offline cycle without hidden global state.
- **Rejected alternative(s)**: Redux store — PRD does not need complex client state. Hard-coded ontology — would bypass backend validation.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
Do not add direct Python or filesystem imports. Test mocks browser `fetch`; backend contract changes require updating both `App.test.jsx` and API tests. `mutation.original_config` is nullable; only read it when `mutated_config` exists. SSE frames may be split arbitrarily; keep `requestCycleStream()` buffer parsing before rendering a packet. `afterPaint()` spaces rendering of already-received real events; never use it to fabricate stage progress. Clear `stageEvents` only in the next Cycle's `onMutate`; clearing them at result delivery recreates the blink.

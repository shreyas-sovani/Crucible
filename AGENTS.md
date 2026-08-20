# AGENTS.md

This file is the canonical source of instructions for any AI coding agent working in this repository (Cursor, Codex, Claude Code, or any other tool that reads AGENTS.md natively or via import). If you are an agent reading this: read this file fully before doing anything else, then read the `AGENTS.md` in every directory you are about to touch.

## Project

**Crucible** — closed-loop adversarial lab for the Mastercard Innovation Challenge @ GFF 2026 (Identify → Simulate → Detect → Mutate). Dual rail (`card` + `upi`). Submission: runnable repo, `.docx` walkthrough, web lab. Deadline 31 Aug 2026.

Do not re-derive product, glossary, architecture, eval rules, or scope from chat. Read:

| Doc | When |
| --- | --- |
| [`CONTEXT.md`](CONTEXT.md) | Before naming anything. Terms are mandatory. No synonyms. |
| [`docs/PRD.md`](docs/PRD.md) | Before implementing or changing behavior. |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Before picking work. Calendar order. Promote `needs-triage` → `ready` → `in-progress` → `done`. |
| This file + subdirectory `AGENTS.md` | Before touching that directory. |

## Section 0 — Things actively in flux right now

- CRU-01 through CRU-20 are implemented against refreshed `CONTEXT.md` and `docs/PRD.md`; `docs/BACKLOG.md` records their test-backed completion.
- Backend is offline-only: Event Envelope schemas, eight behaviourally distinct dual-rail crews, per-user stable entities, world-scaled fraud volume with wave-rotated mule tokens, vectorized causal features (`prior_tx_count` capped at 10), imbalance-aware LightGBM policy, zero-day evaluation, 45-day card-label availability, and a seeded Cycle orchestrator are present.
- `POST /api/cycle` executes real generation → legitimate-only fidelity (four zero-truncated KS gates, ≥50-sample minimum, plus IST 80% business-hour band) → chronology/label availability → training → 1%-FPR operating-point policy on frozen Test → eligible missed-row-SHAP mutation/retraining. Retraining reuses the original Train legitimate traffic and never reads or regenerates Test. Artifacts include per-family zero-day efficacy and token-only evidence catches/misses.
- `POST /api/cycle` remains the completed-artifact contract. Additive `POST /api/cycle/stream` emits real Identify → Simulate → Detect → Mutate boundaries before that same artifact; `frontend/` retains this actual trace above the completed evidence until the next Cycle, not as a timer. The Lab exposes seed input and world-scale presets through spec scale (`90d × 10,000` ≈ 905k Events, ~28 s offline Cycle; verified: test FPR 0.8%, PR-AUC 0.405, zero-day recalls 1.00/0.75, mutation Δ PR-AUC +0.077).
- Launch local Lab with `uv run uvicorn crucible.api.main:app --reload`, then open `http://127.0.0.1:8000/`; install frontend dependencies once with `cd frontend && npm install`.
- No application work is mid-flight. `uv run pytest -q` has 25 passing tests. Before demo use, run both Python and frontend suites and build the frontend after changing its source.
- Dual rail, LightGBM (not a trained GNN), no LangGraph, offline-first demo (no API key required) are locked in the PRD. Do not re-litigate without an ADR in the relevant directory Decision Log.

## Non-negotiables

Details and schemas live in the PRD. Do not violate these even if a task looks local:

- Simulation-only. No live banks, NPCI, card networks, phishing sites, faces, voices, real PANs, CVVs, or exploit kits. PAN tokens only; mask for display/logs.
- Tests describe behavior at module interfaces (TDD vertical slices). No accuracy-as-success. No resampling before split. No label or future leakage into features.
- Deep modules from the PRD; do not add pass-through wrappers. Crew/detector/catalog variation uses adapters at those seams.
- Lab UI consumes only the lab HTTP surface. Copy and names = `CONTEXT.md` terms.
- Feature freeze 31 Aug. No new simulated crews beyond the eight in the PRD.

## The Directory Documentation Protocol (mandatory, every task)

This is the core operating rule. It is not optional and does not depend on task size.

### 1.1 Trigger

Before you report a task as complete, for **every directory where you created, modified, or deleted files during this task**, you must create or update that directory's `AGENTS.md`. This happens before you hand control back, not as a follow-up the user has to ask for.

If a directory you touched does not yet have an `AGENTS.md`, create one using the template in Section 1.3. Do not skip directories because the change felt small; a one-line fix still changes "latest changes" and may still change "why."

### 1.2 What "detailed enough" means

The bar is: **a different agent, with zero prior context, starting a fresh session, reads only this directory's AGENTS.md (plus the root file) and can correctly continue the work without re-deriving anything by reading the whole diff history.**

That means every subdirectory AGENTS.md must answer, concretely, not generically:

- **Ownership**: who or what owns this code conceptually (which subsystem, which responsibility boundary). Not a person's name unless the project genuinely tracks that; think "this belongs to the billing subsystem" not "Shreyas wrote this."
- **Purpose**: what this directory does, in concrete terms, not "utility functions" but "rate-limiting middleware for the public API gateway."
- **What it controls**: what breaks, changes behavior, or becomes inconsistent if this directory's code is wrong or removed. Name the actual downstream effect.
- **Connections**: what this directory imports/depends on, and what depends on it. Name actual paths/modules, not "various parts of the app."
- **Latest changes**: what changed most recently, in this task, with enough specificity that "what changed" is unambiguous (function/file level, not "improved logic").
- **Why this approach, why not the alternative**: the actual decision and the actual rejected alternative(s), with the real reason. "Chose X because Y constraint ruled out Z" is useful. "Chose X because it's better" is not and should not be written.
- **Known gotchas / things not to touch casually**: anything non-obvious that has already burned time once, so it doesn't burn time twice.

If you cannot fill a section with something concrete, write "Not yet determined" rather than inventing filler. Filler is worse than an honest gap because a future agent will trust it.

### 1.3 Subdirectory AGENTS.md Template

Copy this structure exactly when creating a new subdirectory AGENTS.md. Keep section headers stable so agents can scan for them predictably across the whole repo.

```markdown
# AGENTS.md — [directory path]

## Ownership
[Which subsystem/responsibility this belongs to.]

## Purpose
[What this directory does, concretely.]

## What This Controls
[What breaks or changes behavior downstream if this is wrong/removed/changed.]

## Connections
- Depends on: [actual modules/files/services this imports or calls]
- Depended on by: [actual modules/files/services that import or call this]
- External systems touched: [DBs, APIs, queues, etc., if any]

## Current State
[Working / partially implemented / known broken in X way / deliberately stubbed, etc.]

## Decision Log
[Reverse chronological. Each entry: date, what changed, why this approach, why not the alternative(s) considered, who/what task made the call.]

### [YYYY-MM-DD] — [short title]
- **Change**: [what actually changed, file/function level]
- **Reasoning**: [why this approach]
- **Rejected alternative(s)**: [what else was considered and why it was ruled out]
- **Task/session**: [brief pointer to what prompted this, e.g. "fixing race condition in webhook retry"]

## Known Gotchas
[Non-obvious traps, past mistakes, things that look wrong but are intentional, or vice versa.]
```

### 1.4 Updating vs. rewriting

When a directory's AGENTS.md already exists:

- Append a new entry to **Decision Log** rather than deleting old entries. History is the point.
- Overwrite **Ownership**, **Purpose**, **What This Controls**, **Connections**, and **Current State** in place if they are now inaccurate. These should always reflect the present, not the past.
- Never let **Decision Log** grow unbounded without limit if it starts hurting readability. Once it passes roughly 15–20 entries, collapse the oldest ones into a one-paragraph summary block at the bottom titled "Earlier history (condensed)" and keep the recent ones in full.

---

## Session Handoff Protocol

Used when a human is about to run out of context window on the current agent session and is starting a fresh one.

1. Finish the current unit of work to a clean, working state. Do not leave code half-edited mid-function.
2. Run the Section 1 protocol: update every AGENTS.md for every directory touched in this session, even if the session covered multiple unrelated tasks.
3. In the root AGENTS.md's **Section 0 → "Things actively in flux right now"**, update this list to reflect what's genuinely mid-flight so the next agent doesn't assume something is finished when it isn't.
4. Commit. The documentation update must be part of the same commit as the code change it describes, not a separate "docs" commit later, so git history and doc history never diverge. Commit only when the human asks, unless they have already authorized commits for this workstream.
5. When starting the next session, the human will point the new agent at the root AGENTS.md plus the specific subdirectory AGENTS.md files relevant to the next task. The new agent should read those before writing any code.

# AGENTS.md — src/crucible/simulator/

## Ownership
Offline world generation: legitimate dual-rail traffic, Pareto relationships, and eight stateful fraud-crew adapters.

## Purpose
Produces flat Event Envelope DataFrames through `simulate()` by generating Background traffic, overlaying power-law topology, then injecting CrewConfig-bounded fraud events.

## What This Controls
Fidelity distributions, deterministic seed behavior, graph connectivity, event fraud labels, and crew amount limits. Wrong logic here invalidates features, evaluation, and demo claims.

## Connections
- Depends on: `models/event.py`, `models/config.py`, NumPy/Pandas, and constants in [`../../../CONTEXT.md`](../../../CONTEXT.md).
- Depended on by: `features/assembler.py`, `api/main.py`, and simulator tests.
- External systems touched: none; output is always synthetic.

## Current State
Working. Background uses specified grocery/dining and P2M/P2P distributions (zero-truncated normal samplers), exact 80% IST business-hour UPI volume, stable per-user PAN/payer entities, UTC output, and deterministic UUIDv4 values. Topology uses Pareto `a=1.5`. `SIMULATED_CREWS` maps exactly eight canonical vector IDs, each with its own payment-shaped sequence. Scheduled crews repeat once per 35,000 legitimate Events (`CREW_REPEAT_VOLUME`) with time-shifted, entity-rotated waves (`offset_event`), keeping fraud near real-world rates at spec scale. `simulate()` adds `label_available_at`: 30% of card fraud is delayed 45 days, while UPI stays immediate. `resimulate_train_window()` reuses only original Train legitimate records and emits only in-sample fraud before that Train boundary.

## Decision Log

### 2026-08-20 — Spec-scale realism pass (CRU-16/20)
- **Change**: `background.py` — per-user stable `tok_card_user_NNNNNN` PANs and `user_NNNNNN@upi` payers; off-peak UPI timestamps sampled outside the 09:00–21:00 IST window; `np.clip`-ed normals replaced by `_truncated_normal` inverse-CDF sampling. `world.py` — `CREW_REPEAT_VOLUME` wave scaling calling `crews.offset_event`. `crews.py` — `offset_event` shifts a wave by 13h × repeat, re-keys the Event id, and rotates pan/VPA hop tokens with a `_wN` suffix.
- **Reasoning**: Unique per-event PANs made legitimate rolling windows degenerate; uniform off-peak sampling pushed realized business-hour share to 0.90 against the 0.80 spec; clipping created a mass at amount 0.0 that a 315k-sample KS rejects (p=0.000); fixed crew volume collapsed fraud to 0.02% at 90d × 10,000 users, starving the detector, and reused hop tokens let fraud entities accumulate `prior_tx_count` history like legitimate accounts (36% test FPR before the rotation fix).
- **Rejected alternative(s)**: Raising `velocity_per_hour` in defaults — breaks demo-scale density and the chargeback count test contract. Cloning rows without new ids — duplicate `event_id`s. Widening the IST gate to include 0.90 — would paper over a distribution bug with a threshold change.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Made crews distinct and simulation labels time-realistic
- **Change**: Replaced five empty crew subclasses with payment-specific sequence generation in `crews.py`; added chargeback availability and public `resimulate_train_window()` in `world.py` and exported it from `__init__.py`.
- **Reasoning**: Catalog names need observable generation differences, while delayed card labels must be modeled as availability metadata so Event `label` remains eventual ground truth. Reusing Train legitimate records gives mutation the exact same temporal boundary as first fit.
- **Rejected alternative(s)**: One shared burst generator — collapses attack diversity. Labeling delayed fraud `0` — injects false negatives. Recreating rounded `n_days * .70` traffic — can include data after Train and makes frozen-Test claims false.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Scheduled fraud across chronological Cycle windows
- **Change**: Added canonical default CrewConfig factory, deterministic crew Event IDs, and `schedule_crews=True` mode in `simulate()`; in-sample crews emit across Train/Val/Test while zero-day crews emit only in Test anchors.
- **Reasoning**: Former adapters generated only after Background ended, so Train had no fraud and detector orchestration could not run honestly.
- **Rejected alternative(s)**: Injecting fraud labels directly in Loop — bypasses crew adapters. Scheduling zero-day crews before Test — leaks held-out behavior into fitting windows.
- **Task/session**: Diagnose and complete no-op Run Offline Cycle.

### 2026-08-20 — Added complete offline simulation pipeline
- **Change**: Added `background.py`, `topology.py`, `crews.py`, and `world.py` with public `generate_background()` and `simulate()`.
- **Reasoning**: Keep distribution, graph, adapter, and composition concerns separate while offering one deep public facade.
- **Rejected alternative(s)**: Live payments or network-backed data — prohibited by simulation-only rule. One generic crew without named adapters — PRD requires eight explicit adapters.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
`simulate()` defaults to canonical 10,000 users, so demo endpoints deliberately request a smaller explicit population. `schedule_crews=False` preserves one-batch adapter tests; only closed Cycle uses scheduling. `merchant_id` is a topology-only frame column; it is not an Event payload field. `label_available_at` is simulation/evaluation metadata, not an Event Envelope field. `resimulate_train_window()` must never be replaced with a fresh duration-based `simulate()` call. KS fidelity gates compare against the zero-truncated normal CDF, not the plain normal — changing `_truncated_normal` requires re-checking all four gates at spec scale. Wave rotation means fraud `prior_tx_count` stays 0–5; do not remove token rotation without re-checking test FPR at 90d × 10,000 users.

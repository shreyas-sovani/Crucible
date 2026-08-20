# AGENTS.md — src/crucible/features/

## Ownership
Leakage-safe numerical feature assembly.

## Purpose
Converts time-ordered Event Envelope frames into feature matrix, names, and inspectable frame with strictly historical windows.

## What This Controls
Train/test honesty. Incorrect history order or label propagation would make detector scores falsely optimistic and invalidate zero-day evidence.

## Connections
- Depends on: Pandas/NumPy and flat frames from `simulator/world.py`.
- Depended on by: detector training, mutator feature attribution, and `tests/test_features.py`.
- External systems touched: none.

## Current State
Working. Exposes `last_5_amounts`, `last_10_mccs`, `sum_amount_24h`, `count_tx_1h`, capped `prior_tx_count` (`PRIOR_TX_CAP = 10`), geo/velocity rules, and telemetry pass-through. `_causal_windows` is vectorized (stable per-entity grouping, prefix sums, `searchsorted` time cutoffs, first-occurrence distinct counting); an exact loop reference lives in `tests/test_features.py`. Labels never enter output; `future` columns raise `LeakageError`.

## Decision Log

### 2026-08-20 — Vectorized windows plus capped new-account feature (CRU-17/20)
- **Change**: Replaced the per-row Python history loop with per-entity NumPy aggregation; added `prior_tx_count = min(prior same-entity rows, 10)`. Timestamps forced through `datetime64[ns]` before integer cutoff math.
- **Reasoning**: The loop made the spec-scale 90d × 10,000-user Cycle (~905k Events) infeasible; vectorized assembly runs in ~4 s. `prior_tx_count` is the causal new-account signal separating fresh mule entities from aged legitimate accounts; the saturation cap keeps it stationary across chronological splits (raw counts drift with window position and drove test FPR to 36% before capping). Forcing `datetime64[ns]` is required because this pandas build stores non-nano units by default and silently broke hour/day cutoff arithmetic.
- **Rejected alternative(s)**: pandas `rolling('1h')` per group — different boundary semantics and slow apply paths for the distinct-MCC window. Uncapped `prior_tx_count` — nonstationary across Train/Val/Test. Dropping the feature — removes the strongest honest fresh-entity signal.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Implemented strict-causal assembler
- **Change**: Added `FeatureSet`, `LeakageError`, and `assemble_features()`.
- **Reasoning**: Per-entity history is read before current Event append, making causality explicit and inspectable.
- **Rejected alternative(s)**: Pandas rolling windows with default inclusion semantics — easy to include current or future rows accidentally. Labels as implicit feature columns — prohibited leakage.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
`last_5_amounts` is historical mean and `last_10_mccs` is historical distinct-count so output stays numerical. Do not rename them without updating model consumers. `_distinct_previous_values` counts distinct values in the previous 10 rows, which equals "previous 10 non-null MCCs" only because an entity never mixes card and UPI rows — do not introduce mixed-rail entities without revisiting it.

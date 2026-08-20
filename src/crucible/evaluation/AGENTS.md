# AGENTS.md — src/crucible/evaluation/

## Ownership
Chronological validation, zero-day masking, and business-loss calculations.

## Purpose
Splits Event frames into 70/15/15 time windows, masks two zero-day families only before Test, and computes USD expected loss for APPROVEd fraud.

## What This Controls
Zero-day honesty and loss claims. Mistakes can train on a held-out crew or charge loss for blocked/legitimate Events.

## Connections
- Depends on: `detector/model.py` Decision enum, Pandas, and `CONTEXT.md` constants.
- Depended on by: training orchestration, Loop review, API extensions, and evaluation tests.
- External systems touched: none.

## Current State
Working. Holds out `agentic_checkout` and `remittance_injection`; marks Train/Validation labels available only by each window cutoff; `observed_supervision()` drops unavailable labels rather than turning them into legitimate examples. Test keeps eventual ground truth. Converts UPI INR at fixed 84.0 per USD only for fraud APPROVEs.

## Decision Log

### 2026-08-20 — Added label-availability supervision boundary
- **Change**: `split_chronologically()` now adds `label_observed` from `label_available_at`; added public `observed_supervision()`.
- **Reasoning**: Card fraud delayed by 45 days cannot enter a training or validation label set until available. Filtering preserves its unknown state without corrupting class `0`.
- **Rejected alternative(s)**: Relabeling delayed fraud as legitimate — false-negative label leakage. Applying availability to frozen Test scoring — hides eventual ground truth instead of evaluating a mature holdout.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Added chronological zero-day harness
- **Change**: Added `DatasetSplits`, `split_chronologically()`, `ZERO_DAY_HOLDOUTS`, and `expected_loss()`.
- **Reasoning**: Label masking preserves chronological windows while preventing holdout fraud labels from entering training and validation.
- **Rejected alternative(s)**: Random split — violates PRD chronology. Mutating/dropping Test holdouts — removes required zero-day evaluation.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
Masking changes labels only in Train and Validation. Keep original Test labels intact and never add holdout families to mutator input. Train/Validation callers must use `observed_supervision()`; raw split frames include delayed fraud for auditability but are not fit-ready.

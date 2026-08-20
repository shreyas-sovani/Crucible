"""Chronological split and zero-day label-masking rules."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from crucible.detector.model import Decision


ZERO_DAY_HOLDOUTS = ("agentic_checkout", "remittance_injection")


@dataclass(frozen=True)
class DatasetSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def split_chronologically(events: pd.DataFrame, holdout_families: tuple[str, ...] = ZERO_DAY_HOLDOUTS) -> DatasetSplits:
    """Split 70/15/15 and expose only labels available inside each fit window."""

    if "timestamp" not in events or "family" not in events or "label" not in events:
        msg = "Events require timestamp, family, and label columns for evaluation."
        raise ValueError(msg)
    ordered = events.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], utc=True)
    ordered = ordered.sort_values("timestamp", kind="stable").reset_index(drop=True)
    train_end = int(len(ordered) * 0.70)
    validation_end = int(len(ordered) * 0.85)
    train = ordered.iloc[:train_end].copy()
    validation = ordered.iloc[train_end:validation_end].copy()
    test = ordered.iloc[validation_end:].copy()
    for split in (train, validation):
        _mark_label_observation(split)
        split.loc[split["family"].isin(holdout_families), "label"] = 0
        split.loc[split["family"].isin(holdout_families), "label_observed"] = False
    # Test labels are retained as eventual ground truth. They never enter fit or OP selection.
    test["label_observed"] = True
    return DatasetSplits(train=train, validation=validation, test=test)


def observed_supervision(events: pd.DataFrame) -> pd.DataFrame:
    """Return rows whose labels were available at the relevant training-window cutoff."""

    if "label_observed" not in events:
        return events.copy()
    return events.loc[events["label_observed"].eq(True)].copy()


def _mark_label_observation(split: pd.DataFrame) -> None:
    availability = pd.to_datetime(split.get("label_available_at", split["timestamp"]), utc=True)
    cutoff = pd.to_datetime(split["timestamp"], utc=True).max()
    # Legitimate labels are known at event time; delayed fraud is excluded, never relabelled as legitimate.
    split["label_observed"] = split["label"].eq(0) | availability.le(cutoff)


def expected_loss(events: pd.DataFrame, decisions: list[Decision]) -> float:
    """Return USD loss for fraud events approved by policy, with INR fixed at 84/USD."""

    if len(events) != len(decisions):
        msg = "events and decisions must have equal length."
        raise ValueError(msg)
    total = 0.0
    for (_, event), decision in zip(events.iterrows(), decisions, strict=True):
        if event.get("label") != 1 or decision != Decision.APPROVE:
            continue
        if event.get("rail") == "card":
            total += float(event.get("amount_usd") or 0.0)
        elif event.get("rail") == "upi":
            total += float(event.get("amount_inr") or 0.0) / 84.0
    return total

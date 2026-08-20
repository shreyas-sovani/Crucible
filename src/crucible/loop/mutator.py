"""SHAP-guided CrewConfig mutation with strict zero-day exclusion."""

from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd

from crucible.evaluation.harness import ZERO_DAY_HOLDOUTS
from crucible.models.config import CrewConfig


IN_SAMPLE_FAMILIES = {
    "deepfake_kyc",
    "synthetic_merchant",
    "app_scam",
    "cnp_testing",
    "first_party",
    "bec",
}


class SHAPCapableModel(Protocol):
    def shap_values(self, X: np.ndarray) -> np.ndarray: ...


def mutate_config(
    model: SHAPCapableModel,
    events: pd.DataFrame,
    feature_matrix: np.ndarray,
    feature_names: tuple[str, ...],
    config: CrewConfig,
) -> CrewConfig:
    """Return a bounded mutation from in-sample approved fraud misses only."""

    if config.family in ZERO_DAY_HOLDOUTS or config.family not in IN_SAMPLE_FAMILIES:
        return config
    miss_mask = (
        events["family"].eq(config.family)
        & events["label"].eq(1)
        & events["decision"].astype(str).eq("APPROVE")
    )
    misses = events.loc[miss_mask]
    if misses.empty:
        return config
    missed_rows = feature_matrix[np.flatnonzero(miss_mask.to_numpy())]
    top_feature = top_shap_features(model, missed_rows, feature_names)[0]
    if "amount" in top_feature:
        amount = _maximum_amount(misses)
        lower, upper = config.amount_bounds
        return config.model_copy(update={"amount_bounds": (lower, min(upper, max(lower, amount)))})
    if "count" in top_feature or "velocity" in top_feature:
        return config.model_copy(update={"velocity_per_hour": max(1, config.velocity_per_hour - 1)})
    return config.model_copy(update={"max_hop_count": max(1, config.max_hop_count - 1)})


def top_shap_features(
    model: SHAPCapableModel,
    feature_matrix: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    count: int = 3,
) -> tuple[str, ...]:
    """Return up to three most isolating numeric signals for eligible misses."""

    contributions = np.asarray(model.shap_values(feature_matrix), dtype=float)
    if contributions.ndim != 2 or contributions.shape[1] != len(feature_names):
        msg = "SHAP contributions must match supplied feature names."
        raise ValueError(msg)
    order = np.argsort(np.abs(contributions).mean(axis=0))[::-1][:count]
    return tuple(feature_names[index] for index in order)


def _maximum_amount(events: pd.DataFrame) -> float:
    usd = pd.to_numeric(events.get("amount_usd"), errors="coerce")
    inr = pd.to_numeric(events.get("amount_inr"), errors="coerce")
    amounts = usd.where(usd.notna(), inr).dropna()
    return float(amounts.max()) if not amounts.empty else 0.0

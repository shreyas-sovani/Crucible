"""Power-law relationship overlay for simulated merchant and UPI payee graphs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_power_law_topology(frame: pd.DataFrame, seed: int, *, alpha: float = 1.5) -> pd.DataFrame:
    """Return a copy with Pareto-weighted merchant and payee connectivity."""

    if alpha <= 0:
        msg = "alpha must be positive."
        raise ValueError(msg)
    result = frame.copy()
    rng = np.random.default_rng(seed)
    card_mask = result["rail"].eq("card")
    upi_mask = result["rail"].eq("upi")
    result["merchant_id"] = None
    result.loc[card_mask, "merchant_id"] = _power_law_nodes(card_mask.sum(), "merchant", rng, alpha)
    result.loc[upi_mask, "payee_vpa"] = _power_law_nodes(upi_mask.sum(), "payee", rng, alpha)
    return result


def degree_histogram(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Return relationship degree counts for Generate-view fidelity rendering."""

    cards = frame.loc[frame["rail"].eq("card"), "merchant_id"].dropna().value_counts()
    upi = frame.loc[frame["rail"].eq("upi"), "payee_vpa"].dropna().value_counts()
    return {
        "merchant": {str(node): int(count) for node, count in cards.items()},
        "payee": {str(node): int(count) for node, count in upi.items()},
    }


def _power_law_nodes(count: int, prefix: str, rng: np.random.Generator, alpha: float) -> list[str]:
    if count == 0:
        return []
    node_count = max(2, int(np.sqrt(count)))
    weights = rng.pareto(alpha, node_count) + 1.0
    probabilities = weights / weights.sum()
    selections = rng.choice(node_count, size=count, p=probabilities)
    return [f"{prefix}_{selection:04d}" for selection in selections]

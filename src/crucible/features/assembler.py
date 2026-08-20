"""Strictly causal Event Envelope feature assembly."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


class LeakageError(ValueError):
    """Raised when an input advertises a future-derived feature."""


PRIOR_TX_CAP = 10


@dataclass(frozen=True)
class FeatureSet:
    """Numerical matrix, stable feature names, and inspectable feature frame."""

    values: np.ndarray
    names: tuple[str, ...]
    frame: pd.DataFrame


def assemble_features(events: pd.DataFrame) -> FeatureSet:
    """Build causal windows using only records strictly earlier than each Event."""

    leaking_columns = [column for column in events.columns if "future" in column.lower()]
    if leaking_columns:
        msg = f"Future-derived columns are forbidden: {leaking_columns}."
        raise LeakageError(msg)
    required = {"timestamp", "rail", "device_country"}
    missing = required.difference(events.columns)
    if missing:
        msg = f"Events missing required columns: {sorted(missing)}."
        raise ValueError(msg)

    ordered = events.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], utc=True)
    ordered = ordered.sort_values("timestamp", kind="stable").reset_index(drop=True)
    ordered["_amount"] = _amounts(ordered)
    ordered["_entity"] = _entity_keys(ordered)
    windows = _causal_windows(ordered)
    geo_mismatch = _geo_mismatch(ordered)
    telemetry = {
        "v_cip_injection_flag": _numeric_column(ordered, "v_cip_injection_flag"),
        "browser_dom_anomaly_score": _numeric_column(ordered, "browser_dom_anomaly_score"),
        "remittance_prompt_score": _numeric_column(ordered, "remittance_prompt_score"),
    }
    feature_frame = pd.DataFrame(
        {
            **windows,
            "geo_mismatch": geo_mismatch.astype(int),
            "velocity_spike": (windows["count_tx_1h"] > 5).astype(int),
            **telemetry,
        }
    )
    return FeatureSet(
        values=feature_frame.to_numpy(dtype=float),
        names=tuple(feature_frame.columns),
        frame=feature_frame,
    )


def _amounts(events: pd.DataFrame) -> pd.Series:
    usd = pd.to_numeric(events.get("amount_usd", pd.Series(np.nan, index=events.index)), errors="coerce")
    inr = pd.to_numeric(events.get("amount_inr", pd.Series(np.nan, index=events.index)), errors="coerce")
    return usd.where(usd.notna(), inr).fillna(0.0).astype(float)


def _entity_keys(events: pd.DataFrame) -> pd.Series:
    pan = events.get("pan_token", pd.Series(None, index=events.index)).fillna("")
    payer = events.get("payer_vpa", pd.Series(None, index=events.index)).fillna("")
    keys = pd.Series(np.where(events["rail"].eq("card"), pan, payer), index=events.index, dtype="object")
    return keys.mask(keys.eq(""), "event_" + events.index.astype(str))


def _causal_windows(events: pd.DataFrame) -> dict[str, np.ndarray]:
    """Vectorized per-entity causal aggregates, exactly matching loop semantics.

    Rows are grouped stably by entity so within-group order stays chronological;
    every aggregate then reads only strictly-earlier rows of the same entity.
    """

    size = len(events)
    last_5 = np.zeros(size)
    last_10_mccs = np.zeros(size)
    sum_24h = np.zeros(size)
    count_1h = np.zeros(size, dtype=int)
    prior_count = np.zeros(size)
    if size == 0:
        return {
            "last_5_amounts": last_5,
            "last_10_mccs": last_10_mccs,
            "sum_amount_24h": sum_24h,
            "count_tx_1h": count_1h,
            "prior_tx_count": prior_count,
        }

    ordered = events.sort_values("_entity", kind="stable")
    positions = np.asarray(ordered.index, dtype=int)
    entities = ordered["_entity"].to_numpy(dtype=object)
    timestamps = ordered["timestamp"].to_numpy(dtype="datetime64[ns]").astype("int64")
    amounts = ordered["_amount"].to_numpy(dtype=float)
    mcc_column = ordered.get("mcc")
    mccs = pd.to_numeric(mcc_column, errors="coerce").to_numpy(dtype=float) if mcc_column is not None else np.full(size, np.nan)

    boundaries = np.flatnonzero(entities[1:] != entities[:-1]) + 1
    starts = np.concatenate(([0], boundaries))
    ends = np.concatenate((boundaries, [size]))
    for start, end in zip(starts, ends, strict=True):
        count = end - start
        ts = timestamps[start:end]
        amount = amounts[start:end]
        row_positions = positions[start:end]

        prefix = np.concatenate(([0.0], np.cumsum(amount)))
        indices = np.arange(count)
        window_start = np.maximum(indices - 5, 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_5 = (prefix[indices] - prefix[window_start]) / (indices - window_start)
        last_5[row_positions] = np.where(indices > 0, mean_5, 0.0)

        hour_cutoff = np.searchsorted(ts, ts - 3_600_000_000_000, side="left")
        count_1h[row_positions] = indices - hour_cutoff
        day_cutoff = np.searchsorted(ts, ts - 86_400_000_000_000, side="left")
        sum_24h[row_positions] = prefix[indices] - prefix[day_cutoff]

        last_10_mccs[row_positions] = _distinct_previous_values(mccs[start:end])
        # Saturating cap keeps the new-account signal stationary across split windows.
        prior_count[row_positions] = np.minimum(indices, PRIOR_TX_CAP)

    return {
        "last_5_amounts": last_5,
        "last_10_mccs": last_10_mccs,
        "sum_amount_24h": sum_24h,
        "count_tx_1h": count_1h,
        "prior_tx_count": prior_count,
    }


def _distinct_previous_values(values: np.ndarray, *, window: int = 10) -> np.ndarray:
    """Count distinct non-null values among the previous `window` rows per row."""

    count = len(values)
    shifts = np.full((count, window), np.nan)
    for offset in range(1, window + 1):
        shifts[offset:, offset - 1] = values[:-offset]
    present = ~np.isnan(shifts)
    first_seen = present.copy()
    for later in range(1, window):
        for earlier in range(later):
            duplicate = present[:, earlier] & (shifts[:, later] == shifts[:, earlier])
            first_seen[:, later] &= ~duplicate
    return (present & first_seen).sum(axis=1).astype(float)


def _geo_mismatch(events: pd.DataFrame) -> pd.Series:
    merchant = events.get("merchant_country", pd.Series(None, index=events.index))
    return merchant.notna() & events["device_country"].ne(merchant)


def _numeric_column(events: pd.DataFrame, name: str) -> pd.Series:
    values = events.get(name, pd.Series(0.0, index=events.index))
    return pd.to_numeric(values, errors="coerce").fillna(0.0)

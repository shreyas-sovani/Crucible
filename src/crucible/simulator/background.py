"""Deterministic dual-rail legitimate payment traffic generator."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import numpy as np
import pandas as pd
from scipy.special import ndtri
from scipy.stats import norm


_BACKGROUND_START = datetime(2026, 1, 1, tzinfo=UTC)


def generate_background(seed: int, n_days: int, num_users: int) -> pd.DataFrame:
    """Generate one deterministic legitimate payment per user per requested day."""

    if n_days < 1 or num_users < 1:
        msg = "n_days and num_users must both be positive."
        raise ValueError(msg)

    rng = np.random.default_rng(seed)
    event_count = n_days * num_users
    rails = _balanced_rails(event_count, rng)
    days = rng.integers(0, n_days, size=event_count)
    timestamps = _timestamps(rails, days, rng)

    frame = pd.DataFrame(
        {
            "event_id": [_uuid4_from_rng(rng) for _ in range(event_count)],
            "timestamp": timestamps,
            "rail": rails,
            "channel": np.where(rails == "card", "online", "in_app"),
            "device_country": np.where(rails == "card", "US", "IN"),
            "label": np.zeros(event_count, dtype=int),
            "family": "legitimate",
            "vector_id": "background",
            "pan_token": None,
            "mcc": np.nan,
            "amount_usd": np.nan,
            "entry_mode": None,
            "stan": None,
            "merchant_country": None,
            "payer_vpa": None,
            "payee_vpa": None,
            "amount_inr": np.nan,
            "tx_note": None,
            "v_cip_injection_flag": None,
            "browser_dom_anomaly_score": np.nan,
            "remittance_prompt_score": np.nan,
        }
    )
    _populate_card_background(frame, rails == "card", rng, num_users)
    _populate_upi_background(frame, rails == "upi", rng, num_users)
    return frame.sort_values("timestamp", kind="stable").reset_index(drop=True)


def _balanced_rails(event_count: int, rng: np.random.Generator) -> np.ndarray:
    card_count = event_count // 2
    rails = np.array(["card"] * card_count + ["upi"] * (event_count - card_count), dtype=object)
    return rails[rng.permutation(event_count)]


def _timestamps(rails: np.ndarray, days: np.ndarray, rng: np.random.Generator) -> pd.DatetimeIndex:
    seconds = rng.integers(0, 24 * 60 * 60, size=len(rails))
    upi_indices = np.flatnonzero(rails == "upi")
    business_count = int(len(upi_indices) * 0.8)
    business_indices = rng.choice(upi_indices, size=business_count, replace=False)
    off_peak_indices = np.setdiff1d(upi_indices, business_indices)
    # 09:00-21:00 IST converted to UTC; all Event timestamps remain UTC.
    ist_start = 9 * 3600 - (5 * 3600 + 30 * 60)
    ist_end = 21 * 3600 - (5 * 3600 + 30 * 60)
    span = ist_end - ist_start
    seconds[business_indices] = ist_start + rng.integers(0, span, size=business_count)
    # Remaining UPI volume lands outside the window so realized share stays 80%.
    before = rng.integers(0, ist_start, size=len(off_peak_indices))
    after = rng.integers(ist_end, 24 * 3600, size=len(off_peak_indices))
    use_after = rng.random(len(off_peak_indices)) < (24 * 3600 - ist_end) / (24 * 3600 - span)
    seconds[off_peak_indices] = np.where(use_after, after, before)
    return pd.to_datetime(_BACKGROUND_START) + pd.to_timedelta(days, unit="D") + pd.to_timedelta(seconds, unit="s")


def _populate_card_background(frame: pd.DataFrame, mask: np.ndarray, rng: np.random.Generator, num_users: int) -> None:
    count = int(mask.sum())
    if not count:
        return
    kinds = rng.choice(np.array(["grocery", "dining", "other"]), size=count, p=[0.6, 0.2, 0.2])
    mcc = rng.integers(1000, 10000, size=count)
    mcc[mcc == 5411] = 5412
    mcc[mcc == 5812] = 5813
    mcc[kinds == "grocery"] = 5411
    mcc[kinds == "dining"] = 5812
    amounts = rng.uniform(5.0, 200.0, size=count)
    amounts[kinds == "grocery"] = _truncated_normal(rng, 45.0, 15.0, int((kinds == "grocery").sum()))
    amounts[kinds == "dining"] = _truncated_normal(rng, 30.0, 10.0, int((kinds == "dining").sum()))
    positions = np.flatnonzero(mask)
    users = positions % num_users
    frame.loc[positions, "pan_token"] = [f"tok_card_user_{user:06d}" for user in users]
    frame.loc[positions, "mcc"] = mcc
    frame.loc[positions, "amount_usd"] = amounts
    frame.loc[positions, "entry_mode"] = "chip"
    frame.loc[positions, "stan"] = [f"{position % 1_000_000:06d}" for position in positions]
    frame.loc[positions, "merchant_country"] = "US"


def _populate_upi_background(frame: pd.DataFrame, mask: np.ndarray, rng: np.random.Generator, num_users: int) -> None:
    count = int(mask.sum())
    if not count:
        return
    p2m = rng.random(count) < 0.7
    amounts = _truncated_normal(rng, 2000.0, 1000.0, count)
    amounts[p2m] = _truncated_normal(rng, 500.0, 200.0, int(p2m.sum()))
    positions = np.flatnonzero(mask)
    users = positions % num_users
    frame.loc[positions, "payer_vpa"] = [f"user_{user:06d}@upi" for user in users]
    frame.loc[positions, "payee_vpa"] = [
        f"{'merchant' if is_p2m else 'person'}{user:06d}@upi" for user, is_p2m in zip(users, p2m, strict=True)
    ]
    frame.loc[positions, "amount_inr"] = amounts
    frame.loc[positions, "tx_note"] = np.where(p2m, "p2m", "p2p")


def _uuid4_from_rng(rng: np.random.Generator) -> str:
    return str(UUID(bytes=rng.bytes(16), version=4))


def _truncated_normal(rng: np.random.Generator, mean: float, stddev: float, size: int) -> np.ndarray:
    """Sample the declared N(mean, stddev) truncated at zero; amounts must stay >= 0."""

    if size == 0:
        return np.zeros(0)
    lower_cdf = norm.cdf((0.0 - mean) / stddev)
    uniforms = lower_cdf + rng.random(size) * (1.0 - lower_cdf)
    return mean + stddev * ndtri(uniforms)

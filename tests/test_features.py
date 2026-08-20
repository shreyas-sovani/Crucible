import numpy as np
import pandas as pd
import pytest

from crucible.features.assembler import LeakageError, assemble_features


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-08-20T00:00:00Z", "2026-08-20T00:30:00Z"]),
            "rail": ["upi", "upi"],
            "payer_vpa": ["payer@upi", "payer@upi"],
            "payee_vpa": ["merchant@upi", "merchant@upi"],
            "amount_inr": [10.0, 20.0],
            "amount_usd": [None, None],
            "mcc": [None, None],
            "device_country": ["IN", "IN"],
            "merchant_country": [None, None],
            "label": [1, 0],
            "v_cip_injection_flag": [False, False],
            "browser_dom_anomaly_score": [0.0, 0.0],
            "remittance_prompt_score": [0.0, 0.0],
        }
    )


def test_feature_windows_are_strictly_causal_and_labels_are_absent() -> None:
    features = assemble_features(_events())
    second = features.frame.iloc[1]

    assert second["last_5_amounts"] == 10.0
    assert second["sum_amount_24h"] == 10.0
    assert second["count_tx_1h"] == 1
    assert second["velocity_spike"] == 0
    assert "label" not in features.names


def test_feature_assembler_rejects_explicit_future_leakage_column() -> None:
    events = _events().assign(future_fraud_count=[0, 1])

    with pytest.raises(LeakageError):
        assemble_features(events)


def _reference_windows(events: pd.DataFrame) -> pd.DataFrame:
    """Loop reference defining exact causal semantics; production must match it."""

    ordered = events.copy()
    ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], utc=True)
    ordered = ordered.sort_values("timestamp", kind="stable").reset_index(drop=True)
    usd = pd.to_numeric(ordered.get("amount_usd"), errors="coerce")
    inr = pd.to_numeric(ordered.get("amount_inr"), errors="coerce")
    ordered["_amount"] = usd.where(usd.notna(), inr).fillna(0.0).astype(float)
    pan = ordered.get("pan_token", pd.Series(None, index=ordered.index)).fillna("")
    payer = ordered.get("payer_vpa", pd.Series(None, index=ordered.index)).fillna("")
    keys = pd.Series(np.where(ordered["rail"].eq("card"), pan, payer), index=ordered.index, dtype=object)
    ordered["_entity"] = keys.mask(keys.eq(""), "event_" + ordered.index.astype(str))

    rows = np.zeros((len(ordered), 5), dtype=float)
    for _, group in ordered.groupby("_entity", sort=False):
        history: list[tuple[pd.Timestamp, float, float | None]] = []
        for row_index, row in group.iterrows():
            now = row["timestamp"]
            amounts = [amount for _, amount, _ in history]
            mccs = [mcc for _, _, mcc in history if mcc is not None]
            in_day = [a for ts, a, _ in history if now - ts <= pd.Timedelta(hours=24)]
            in_hour = [a for ts, a, _ in history if now - ts <= pd.Timedelta(hours=1)]
            rows[row_index] = [
                float(np.mean(amounts[-5:])) if amounts else 0.0,
                float(len(set(mccs[-10:]))),
                float(np.sum(in_day)) if in_day else 0.0,
                float(len(in_hour)),
                float(min(len(history), 10)),
            ]
            raw_mcc = row.get("mcc")
            history.append((now, float(row["_amount"]), float(raw_mcc) if pd.notna(raw_mcc) else None))
    return pd.DataFrame(rows, columns=["last_5_amounts", "last_10_mccs", "sum_amount_24h", "count_tx_1h", "prior_tx_count"])


def test_vectorized_windows_match_loop_reference_on_random_frames() -> None:
    rng = np.random.default_rng(42)

    for trial in range(5):
        size = int(rng.integers(40, 240))
        is_card = rng.random(size) < 0.5
        base = pd.Timestamp("2026-01-01T00:00:00Z")
        timestamps = base + pd.to_timedelta(
            np.sort(rng.integers(0, 60 * 24 * 3600, size=size)), unit="s"
        )
        users = [f"user_{int(u):03d}" for u in rng.integers(0, 12, size=size)]
        events = pd.DataFrame(
            {
                "timestamp": timestamps,
                "rail": np.where(is_card, "card", "upi"),
                "device_country": np.where(is_card, "US", "IN"),
                "pan_token": [f"tok_{u}" if c else None for u, c in zip(users, is_card, strict=True)],
                "payer_vpa": [f"{u}@upi" if not c else None for u, c in zip(users, is_card, strict=True)],
                "amount_usd": [float(round(a, 2)) if c else None for a, c in zip(rng.uniform(1, 300, size), is_card, strict=True)],
                "amount_inr": [float(round(a, 2)) if not c else None for a, c in zip(rng.uniform(1, 9000, size), is_card, strict=True)],
                "mcc": [int(m) if c else None for m, c in zip(rng.integers(1000, 10000, size), is_card, strict=True)],
                "merchant_country": ["US" if c else None for c in is_card],
            }
        )
        produced = assemble_features(events).frame
        reference = _reference_windows(events)

        assert list(produced.index) == list(reference.index)
        for column in ["last_5_amounts", "last_10_mccs", "sum_amount_24h", "count_tx_1h", "prior_tx_count"]:
            np.testing.assert_allclose(produced[column].to_numpy(), reference[column].to_numpy(), rtol=1e-9, atol=1e-9)

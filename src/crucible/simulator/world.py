"""Composable world simulation facade."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from crucible.models.config import CrewConfig
from crucible.models.event import Event
from crucible.evaluation.harness import ZERO_DAY_HOLDOUTS
from crucible.simulator.background import generate_background
from crucible.simulator.crews import SIMULATED_CREWS, offset_event
from crucible.simulator.topology import apply_power_law_topology

# Scheduled crews repeat once per 35,000 legitimate Events so fraud density
# stays near real-world rates instead of collapsing at spec scale.
CREW_REPEAT_VOLUME = 35_000


def simulate(
    seed: int,
    n_days: int,
    crews: list[CrewConfig],
    *,
    num_users: int = 10_000,
    schedule_crews: bool = False,
) -> pd.DataFrame:
    """Generate deterministic legitimate traffic and overlay configured fraud crews."""

    background = apply_power_law_topology(generate_background(seed=seed, n_days=n_days, num_users=num_users), seed=seed)
    fraud_records: list[dict[str, object]] = []
    for config in crews:
        crew_type = SIMULATED_CREWS.get(config.vector_id)
        if crew_type is None:
            msg = f"No simulated crew adapter for vector_id={config.vector_id!r}."
            raise ValueError(msg)
        events = _scheduled_events(crew_type(), background, config) if schedule_crews else crew_type().generate(background, config)
        fraud_records.extend(_event_record(event) for event in events)
    if not fraud_records:
        return apply_chargeback_lag(background, seed=seed)
    combined = pd.concat([background, pd.DataFrame(fraud_records)], ignore_index=True)
    combined = combined.sort_values("timestamp", kind="stable").reset_index(drop=True)
    return apply_chargeback_lag(combined, seed=seed)


def _scheduled_events(crew: object, background: pd.DataFrame, config: CrewConfig) -> list[Event]:
    """Place normal crews across time while preserving zero-day crews for Test."""

    anchors = (0.90, 0.96) if config.family in ZERO_DAY_HOLDOUTS else (0.12, 0.30, 0.50, 0.70, 0.90)
    repeats = len(background) // CREW_REPEAT_VOLUME + 1
    events: list[Event] = []
    for anchor in anchors:
        end = max(1, int(len(background) * anchor))
        for repeat in range(repeats):
            block = crew.generate(background.iloc[:end], config)  # type: ignore[union-attr]
            events.extend(block if repeat == 0 else [offset_event(event, timedelta(hours=13 * repeat), repeat) for event in block])
    return events


def _event_record(event: Event) -> dict[str, object]:
    record: dict[str, object] = {
        "event_id": str(event.event_id),
        "timestamp": event.timestamp,
        "rail": event.rail,
        "channel": event.channel,
        "device_country": event.device_country,
        "label": event.label,
        "label_available_at": event.timestamp,
        "family": event.family,
        "vector_id": event.vector_id,
        "pan_token": None,
        "mcc": None,
        "amount_usd": None,
        "entry_mode": None,
        "stan": None,
        "merchant_country": None,
        "payer_vpa": None,
        "payee_vpa": None,
        "amount_inr": None,
        "tx_note": None,
        "v_cip_injection_flag": None,
        "browser_dom_anomaly_score": None,
        "remittance_prompt_score": None,
    }
    if event.card_payload is not None:
        record.update(event.card_payload.model_dump())
    if event.upi_payload is not None:
        record.update(event.upi_payload.model_dump())
    if event.genai_telemetry is not None:
        record.update(event.genai_telemetry.model_dump())
    return record


def apply_chargeback_lag(events: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    """Expose delayed labels: exactly 30% of simulated card fraud arrives after 45 days."""

    result = events.copy()
    timestamps = pd.to_datetime(result["timestamp"], utc=True)
    result["label_available_at"] = timestamps
    card_fraud = result["rail"].eq("card") & result["label"].eq(1)
    card_positions = np.flatnonzero(card_fraud.to_numpy())
    delayed_count = int(round(len(card_positions) * 0.30))
    if delayed_count:
        rng = np.random.default_rng(seed)
        delayed_positions = rng.choice(card_positions, size=delayed_count, replace=False)
        result.loc[delayed_positions, "label_available_at"] = timestamps.iloc[delayed_positions] + pd.Timedelta(days=45)
    return result


def resimulate_train_window(train_events: pd.DataFrame, *, crews: list[CrewConfig], seed: int) -> pd.DataFrame:
    """Regenerate only eligible fraud over original Train legitimate traffic.

    `train_events` is already the chronological Train slice. Its legitimate Event
    records are reused verbatim, while new in-sample crew events are bounded by
    the same final Train timestamp. Test data is neither read nor recreated.
    """

    if train_events.empty:
        msg = "train_events must not be empty."
        raise ValueError(msg)
    ordered = train_events.sort_values("timestamp", kind="stable").reset_index(drop=True)
    background = ordered.loc[ordered["family"].eq("legitimate")].copy()
    if background.empty:
        msg = "train_events requires legitimate background traffic."
        raise ValueError(msg)
    window_end = pd.to_datetime(ordered["timestamp"], utc=True).max()
    fraud_records: list[dict[str, object]] = []
    for config in crews:
        if config.family in ZERO_DAY_HOLDOUTS:
            continue
        crew_type = SIMULATED_CREWS.get(config.vector_id)
        if crew_type is None:
            msg = f"No simulated crew adapter for vector_id={config.vector_id!r}."
            raise ValueError(msg)
        scheduled = _scheduled_events(crew_type(), background, config)
        fraud_records.extend(
            _event_record(event)
            for event in scheduled
            if pd.Timestamp(event.timestamp) <= window_end
        )
    regenerated = background if not fraud_records else pd.concat([background, pd.DataFrame(fraud_records)], ignore_index=True)
    regenerated = regenerated.sort_values("timestamp", kind="stable").reset_index(drop=True)
    regenerated = apply_chargeback_lag(regenerated, seed=seed)
    availability = pd.to_datetime(regenerated["label_available_at"], utc=True)
    regenerated["label_observed"] = regenerated["label"].eq(0) | availability.le(window_end)
    return regenerated

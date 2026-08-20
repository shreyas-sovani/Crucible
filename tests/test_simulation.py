import pandas as pd

from crucible.models.config import CrewConfig
from crucible.evaluation.harness import split_chronologically
from crucible.simulator import resimulate_train_window, simulate
from crucible.simulator.crews import default_crew_configs


def test_simulate_overlays_configured_crew_events_on_background() -> None:
    frame = simulate(
        seed=5,
        n_days=1,
        crews=[
            CrewConfig(
                vector_id="Agentic_Checkout",
                family="agentic_checkout",
                rail="card",
                amount_bounds=(50.0, 100.0),
                velocity_per_hour=2,
                max_hop_count=1,
            )
        ],
        num_users=10,
    )

    fraud = frame.loc[frame["family"] == "agentic_checkout"]

    assert len(fraud) == 2
    assert fraud["label"].eq(1).all()
    assert fraud["browser_dom_anomaly_score"].eq(0.95).all()


def test_simulation_applies_context_chargeback_lag_to_thirty_percent_of_card_fraud_only() -> None:
    card = CrewConfig(
        vector_id="Agentic_Checkout",
        family="agentic_checkout",
        rail="card",
        amount_bounds=(50.0, 100.0),
        velocity_per_hour=10,
        max_hop_count=1,
    )
    upi = CrewConfig(
        vector_id="V-CIP_Mule",
        family="deepfake_kyc",
        rail="upi",
        amount_bounds=(100.0, 200.0),
        velocity_per_hour=10,
        max_hop_count=1,
    )

    frame = simulate(seed=7, n_days=1, crews=[card, upi], num_users=10)
    fraud = frame.loc[frame["label"].eq(1)].copy()
    delay_days = (pd.to_datetime(fraud["label_available_at"], utc=True) - pd.to_datetime(fraud["timestamp"], utc=True)).dt.days

    assert delay_days.loc[fraud["rail"].eq("card")].value_counts().to_dict() == {0: 7, 45: 3}
    assert delay_days.loc[fraud["rail"].eq("upi")].eq(0).all()


def test_fraud_volume_scales_with_world_size_and_keeps_event_ids_unique() -> None:
    small = simulate(seed=11, n_days=1, crews=default_crew_configs(), num_users=50, schedule_crews=True)
    large = simulate(seed=11, n_days=30, crews=default_crew_configs(), num_users=3_000, schedule_crews=True)

    small_fraud = int(small["label"].eq(1).sum())
    large_fraud = int(large["label"].eq(1).sum())

    assert small_fraud == 204
    assert large_fraud > 600
    assert large["event_id"].is_unique
    assert large_fraud / len(large) < 0.02


def test_train_window_resimulation_reuses_train_legitimate_events_and_never_crosses_frozen_test_boundary() -> None:
    original = simulate(seed=3, n_days=3, crews=default_crew_configs(), num_users=80, schedule_crews=True)
    splits = split_chronologically(original)

    resimulated = resimulate_train_window(splits.train, crews=default_crew_configs(), seed=3)

    train_legitimate_ids = set(splits.train.loc[splits.train["family"].eq("legitimate"), "event_id"])
    resimulated_legitimate_ids = set(resimulated.loc[resimulated["family"].eq("legitimate"), "event_id"])
    assert resimulated_legitimate_ids == train_legitimate_ids
    assert pd.to_datetime(resimulated["timestamp"], utc=True).max() <= pd.to_datetime(splits.train["timestamp"], utc=True).max()
    assert set(resimulated["event_id"]).isdisjoint(set(splits.test["event_id"]))
    assert not resimulated["family"].isin({"agentic_checkout", "remittance_injection"}).any()

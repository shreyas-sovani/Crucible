import pandas as pd

from crucible.models.config import CrewConfig
from crucible.simulator.crews import SIMULATED_CREWS


def test_every_simulated_crew_emits_events_within_configured_amount_bounds() -> None:
    world = pd.DataFrame({"timestamp": [pd.Timestamp("2026-08-20T00:00:00Z")]})

    assert set(SIMULATED_CREWS) == {
        "V-CIP_Mule",
        "Agentic_Checkout",
        "Prompt_Inject_Copilot",
        "Synthetic_Triangulation",
        "Scaled_Investment_APP",
        "LLM_Card_Testing",
        "Auto_Dispute_Farm",
        "Voice_Clone_Exec",
    }
    for vector_id, crew_type in SIMULATED_CREWS.items():
        rail = "card" if vector_id in {"Agentic_Checkout", "Synthetic_Triangulation", "LLM_Card_Testing", "Auto_Dispute_Farm"} else "upi"
        config = CrewConfig(
            vector_id=vector_id,
            family=f"family_{vector_id}",
            rail=rail,
            amount_bounds=(10.0, 20.0),
            velocity_per_hour=2,
            max_hop_count=2,
        )

        events = crew_type().generate(world, config)

        assert len(events) == 2
        for event in events:
            amount = event.card_payload.amount_usd if event.rail == "card" else event.upi_payload.amount_inr
            assert amount is not None
            assert 10.0 <= amount <= 20.0
            assert event.rail == rail


def test_simulated_crews_emit_distinct_payment_behaviour_profiles() -> None:
    """Catalog diversity must become observable Event-envelope diversity."""

    world = pd.DataFrame({"timestamp": [pd.Timestamp("2026-08-20T00:00:00Z")]})
    expected_profiles = {
        "V-CIP_Mule": ("in_app", None, "vcip_cashout_0@upi", True),
        "Agentic_Checkout": ("online", 5812, None, 0.95),
        "Prompt_Inject_Copilot": ("in_app", None, "beneficiary_0@upi", 0.95),
        "Synthetic_Triangulation": ("online", 5734, None, None),
        "Scaled_Investment_APP": ("in_app", None, "investment_pool_0@upi", None),
        "LLM_Card_Testing": ("online", 5999, None, None),
        "Auto_Dispute_Farm": ("pos", 5411, None, None),
        "Voice_Clone_Exec": ("in_app", None, "exec_vendor_0@upi", None),
    }

    observed_profiles = {}
    for vector_id, crew_type in SIMULATED_CREWS.items():
        rail = "card" if vector_id in {"Agentic_Checkout", "Synthetic_Triangulation", "LLM_Card_Testing", "Auto_Dispute_Farm"} else "upi"
        event = crew_type().generate(
            world,
            CrewConfig(
                vector_id=vector_id,
                family=f"family_{vector_id}",
                rail=rail,
                amount_bounds=(10.0, 20.0),
                velocity_per_hour=2,
                max_hop_count=2,
            ),
        )[0]
        telemetry = event.genai_telemetry
        observed_profiles[vector_id] = (
            event.channel,
            event.card_payload.mcc if event.card_payload else None,
            event.upi_payload.payee_vpa if event.upi_payload else None,
            (
                telemetry.v_cip_injection_flag
                if telemetry and telemetry.v_cip_injection_flag
                else telemetry.browser_dom_anomaly_score
                if telemetry and telemetry.browser_dom_anomaly_score is not None
                else telemetry.remittance_prompt_score
                if telemetry
                else None
            ),
        )

    assert observed_profiles == expected_profiles

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from crucible.models.config import CrewConfig
from crucible.models.event import CardPayload, Event, UPIPayload


def _event_fields(rail: str) -> dict[str, object]:
    return {
        "event_id": uuid4(),
        "timestamp": datetime(2026, 8, 20, tzinfo=UTC),
        "rail": rail,
        "channel": "online",
        "device_country": "IN" if rail == "upi" else "US",
        "label": 0,
        "family": "legitimate",
        "vector_id": "background",
    }


def test_event_rejects_raw_pan_and_mixed_rail_payloads() -> None:
    with pytest.raises((ValidationError, ValueError)):
        CardPayload(
            pan_token="4111111111111111",
            mcc=5411,
            amount_usd=45.0,
            entry_mode="chip",
            stan="000001",
            merchant_country="US",
        )

    with pytest.raises(ValidationError):
        Event(
            **_event_fields("upi"),
            card_payload=CardPayload(
                pan_token="tok_card_001",
                mcc=5411,
                amount_usd=45.0,
                entry_mode="chip",
                stan="000001",
                merchant_country="US",
            ),
        )

    event = Event(
        **_event_fields("upi"),
        upi_payload=UPIPayload(
            payer_vpa="payer@upi",
            payee_vpa="merchant@upi",
            amount_inr=500.0,
            tx_note="groceries",
        ),
    )

    assert event.upi_payload is not None


def test_crew_config_requires_ordered_amount_bounds() -> None:
    config = CrewConfig(
        vector_id="Agentic_Checkout",
        family="agentic_checkout",
        rail="card",
        amount_bounds=(10.0, 100.0),
        velocity_per_hour=3,
        max_hop_count=2,
    )

    assert config.amount_bounds == (10.0, 100.0)

    with pytest.raises(ValidationError):
        CrewConfig(
            vector_id="Agentic_Checkout",
            family="agentic_checkout",
            rail="card",
            amount_bounds=(100.0, 10.0),
            velocity_per_hour=3,
            max_hop_count=2,
        )

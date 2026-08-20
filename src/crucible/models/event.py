"""Pydantic contracts for Crucible's unified payment Event Envelope."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CardPayload(BaseModel):
    """Card-only transaction fields; never accepts a raw PAN."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pan_token: str = Field(min_length=1)
    mcc: int = Field(ge=1, le=9999)
    amount_usd: float = Field(ge=0)
    entry_mode: str = Field(min_length=1)
    stan: str = Field(min_length=1)
    merchant_country: str = Field(pattern=r"^[A-Z]{2}$")

    @field_validator("pan_token")
    @classmethod
    def reject_raw_pan(cls, value: str) -> str:
        if re.search(r"(?<!\d)\d{13,19}(?!\d)", value):
            msg = "pan_token must not contain a 13-19 digit PAN."
            raise ValueError(msg)
        return value


class UPIPayload(BaseModel):
    """UPI-only transaction fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    payer_vpa: str = Field(min_length=3)
    payee_vpa: str = Field(min_length=3)
    amount_inr: float = Field(ge=0)
    tx_note: str


class GenAITelemetry(BaseModel):
    """Optional GenAI telemetry attached to a payment Event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    v_cip_injection_flag: bool | None = None
    browser_dom_anomaly_score: float | None = Field(default=None, ge=0, le=1)
    remittance_prompt_score: float | None = Field(default=None, ge=0, le=1)


class Event(BaseModel):
    """One valid card or UPI payment Event Envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID
    timestamp: datetime
    rail: Literal["card", "upi"]
    channel: Literal["online", "pos", "in_app"]
    device_country: str = Field(pattern=r"^[A-Z]{2}$")
    label: Literal[0, 1] | None
    family: str = Field(min_length=1)
    vector_id: str = Field(min_length=1)
    card_payload: CardPayload | None = None
    upi_payload: UPIPayload | None = None
    genai_telemetry: GenAITelemetry | None = None

    @field_validator("event_id")
    @classmethod
    def require_uuid4(cls, value: UUID) -> UUID:
        if value.version != 4:
            msg = "event_id must be UUIDv4."
            raise ValueError(msg)
        return value

    @field_validator("timestamp")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            msg = "timestamp must be UTC and tz-aware."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def require_matching_payload(self) -> "Event":
        if self.rail == "card" and (self.card_payload is None or self.upi_payload is not None):
            msg = "card Event requires card_payload and forbids upi_payload."
            raise ValueError(msg)
        if self.rail == "upi" and (self.upi_payload is None or self.card_payload is not None):
            msg = "upi Event requires upi_payload and forbids card_payload."
            raise ValueError(msg)
        return self

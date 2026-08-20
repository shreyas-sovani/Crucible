"""Validated configuration passed from a vector to its fraud crew adapter."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CrewConfig(BaseModel):
    """Mutation-safe bounds for one simulated fraud crew."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    vector_id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    rail: Literal["card", "upi"]
    amount_bounds: tuple[float, float]
    velocity_per_hour: int = Field(ge=1)
    max_hop_count: int = Field(ge=1)

    @model_validator(mode="after")
    def require_valid_bounds(self) -> "CrewConfig":
        lower, upper = self.amount_bounds
        if lower < 0 or upper < 0 or lower > upper:
            msg = "amount_bounds must be non-negative and ordered (min, max)."
            raise ValueError(msg)
        return self

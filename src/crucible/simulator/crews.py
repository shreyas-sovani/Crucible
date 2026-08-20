"""Behavioural crew adapters for Crucible's eight simulated fraud vectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from hashlib import blake2b
from uuid import UUID

import pandas as pd

from crucible.models.config import CrewConfig
from crucible.models.event import CardPayload, Event, GenAITelemetry, UPIPayload
from crucible.ontology.schema import load_ontology


class BaseCrew(ABC):
    """Shared Event-envelope construction; each adapter owns its behaviour."""

    @abstractmethod
    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        """Generate one configured, payment-shaped simulated attack sequence."""

    def _card_event(
        self,
        config: CrewConfig,
        timestamp: datetime,
        amount: float,
        index: int,
        *,
        mcc: int,
        entry_mode: str,
        merchant_country: str = "US",
        pan_token_prefix: str,
        telemetry: GenAITelemetry | None = None,
    ) -> Event:
        return Event(
            event_id=_deterministic_event_id(config, timestamp, index),
            timestamp=timestamp,
            rail="card",
            channel="pos" if entry_mode == "chip" else "online",
            device_country="US",
            label=1,
            family=config.family,
            vector_id=config.vector_id,
            card_payload=CardPayload(
                pan_token=f"{pan_token_prefix}_{index % config.max_hop_count}",
                mcc=mcc,
                amount_usd=amount,
                entry_mode=entry_mode,
                stan=f"{index:06d}",
                merchant_country=merchant_country,
            ),
            genai_telemetry=telemetry,
        )

    def _upi_event(
        self,
        config: CrewConfig,
        timestamp: datetime,
        amount: float,
        index: int,
        *,
        payer_prefix: str,
        payee_prefix: str,
        tx_note: str,
        telemetry: GenAITelemetry | None = None,
    ) -> Event:
        return Event(
            event_id=_deterministic_event_id(config, timestamp, index),
            timestamp=timestamp,
            rail="upi",
            channel="in_app",
            device_country="IN",
            label=1,
            family=config.family,
            vector_id=config.vector_id,
            upi_payload=UPIPayload(
                payer_vpa=f"{payer_prefix}_{index % config.max_hop_count}@upi",
                payee_vpa=f"{payee_prefix}_{index % config.max_hop_count}@upi",
                amount_inr=amount,
                tx_note=tx_note,
            ),
            genai_telemetry=telemetry,
        )


class VCIPMuleCrew(BaseCrew):
    """V-CIP-approved mule accounts fan funds into short-hop cash-out VPAs."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._upi_event(
                config,
                start + timedelta(minutes=index),
                _amount(config, 0.20 + 0.08 * (index % 4)),
                index,
                payer_prefix="verified_mule",
                payee_prefix="vcip_cashout",
                tx_note="mule settlement",
                telemetry=GenAITelemetry(v_cip_injection_flag=True),
            )
            for index in range(config.velocity_per_hour)
        ]


class AgenticCheckoutCrew(BaseCrew):
    """Browser-steered cross-border checkout attempts on a dining merchant."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._card_event(
                config,
                start + timedelta(seconds=20 * index),
                _amount(config, 0.35 + 0.10 * (index % 5)),
                index,
                mcc=5812,
                entry_mode="online",
                merchant_country="CA",
                pan_token_prefix="tok_agentic_checkout",
                telemetry=GenAITelemetry(browser_dom_anomaly_score=0.95),
            )
            for index in range(config.velocity_per_hour)
        ]


class PromptInjectCopilotCrew(BaseCrew):
    """Malicious remittance instruction concealed in beneficiary payment notes."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._upi_event(
                config,
                start + timedelta(minutes=2 * index),
                _amount(config, 0.55 + 0.05 * (index % 3)),
                index,
                payer_prefix="copilot_operator",
                payee_prefix="beneficiary",
                tx_note="beneficiary invoice",
                telemetry=GenAITelemetry(remittance_prompt_score=0.95),
            )
            for index in range(config.velocity_per_hour)
        ]


class SyntheticTriangulationCrew(BaseCrew):
    """Synthetic merchant card purchases that concentrate on one merchant type."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._card_event(
                config,
                start + timedelta(minutes=3 * index),
                _amount(config, 0.72 - 0.04 * (index % 4)),
                index,
                mcc=5734,
                entry_mode="online",
                pan_token_prefix="tok_synthetic_buyer",
            )
            for index in range(config.velocity_per_hour)
        ]


class ScaledInvestmentAPPCrew(BaseCrew):
    """Investment-app social engineering with a deliberately rising contribution ladder."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        count = max(1, config.velocity_per_hour)
        return [
            self._upi_event(
                config,
                start + timedelta(minutes=5 * index),
                _amount(config, ((index + 1) / count) ** 2),
                index,
                payer_prefix="retail_investor",
                payee_prefix="investment_pool",
                tx_note="investment contribution",
            )
            for index in range(config.velocity_per_hour)
        ]


class LLMCardTestingCrew(BaseCrew):
    """Low-value card-not-present probes before a larger authorization is attempted."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._card_event(
                config,
                start + timedelta(seconds=12 * index),
                _amount(config, 0.03 + 0.02 * (index % 5)),
                index,
                mcc=5999,
                entry_mode="credential_on_file",
                pan_token_prefix="tok_card_probe",
            )
            for index in range(config.velocity_per_hour)
        ]


class AutoDisputeFarmCrew(BaseCrew):
    """First-party dispute pattern represented by ordinary-looking grocery purchases."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._card_event(
                config,
                start + timedelta(hours=index),
                _amount(config, 0.16 + 0.02 * (index % 3)),
                index,
                mcc=5411,
                entry_mode="chip",
                pan_token_prefix="tok_dispute_farm",
            )
            for index in range(config.velocity_per_hour)
        ]


class VoiceCloneExecCrew(BaseCrew):
    """Executive-impersonation settlements routed to a rotating vendor set."""

    def generate(self, world: pd.DataFrame, config: CrewConfig) -> list[Event]:
        start = _next_timestamp(world)
        return [
            self._upi_event(
                config,
                start + timedelta(minutes=7 * index),
                _amount(config, 0.80 + 0.04 * (index % 3)),
                index,
                payer_prefix="finance_operator",
                payee_prefix="exec_vendor",
                tx_note="urgent vendor settlement",
            )
            for index in range(config.velocity_per_hour)
        ]


SIMULATED_CREWS: dict[str, type[BaseCrew]] = {
    "V-CIP_Mule": VCIPMuleCrew,
    "Agentic_Checkout": AgenticCheckoutCrew,
    "Prompt_Inject_Copilot": PromptInjectCopilotCrew,
    "Synthetic_Triangulation": SyntheticTriangulationCrew,
    "Scaled_Investment_APP": ScaledInvestmentAPPCrew,
    "LLM_Card_Testing": LLMCardTestingCrew,
    "Auto_Dispute_Farm": AutoDisputeFarmCrew,
    "Voice_Clone_Exec": VoiceCloneExecCrew,
}


def default_crew_configs() -> list[CrewConfig]:
    """Return offline default configurations for eight canonical simulated crews."""

    configs: list[CrewConfig] = []
    for vector in load_ontology():
        if vector.status != "simulated":
            continue
        amount_bounds = (1.0, 250.0) if vector.rail == "card" else (100.0, 3_000.0)
        configs.append(
            CrewConfig(
                vector_id=vector.id,
                family=vector.family,
                rail=vector.rail,
                amount_bounds=amount_bounds,
                velocity_per_hour=6,
                max_hop_count=3,
            )
        )
    return configs


def _amount(config: CrewConfig, fraction: float) -> float:
    lower, upper = config.amount_bounds
    return lower + (upper - lower) * min(1.0, max(0.0, fraction))


def offset_event(event: Event, offset: timedelta, repeat_index: int) -> Event:
    """Return a time-shifted copy with fresh entity tokens and a deterministic id.

    Each repeated crew wave rotates its pan/VPA hop tokens so later waves behave
    like fresh mule accounts instead of accumulating history on one entity.
    """

    timestamp = event.timestamp + offset
    material = f"{event.vector_id}|{timestamp.isoformat()}|r{repeat_index}".encode()
    updates: dict[str, object] = {
        "timestamp": timestamp,
        "event_id": UUID(bytes=blake2b(material, digest_size=16).digest(), version=4),
    }
    wave = f"_w{repeat_index}"
    if event.card_payload is not None:
        updates["card_payload"] = event.card_payload.model_copy(
            update={"pan_token": f"{event.card_payload.pan_token}{wave}"}
        )
    if event.upi_payload is not None:
        updates["upi_payload"] = event.upi_payload.model_copy(
            update={
                "payer_vpa": f"{event.upi_payload.payer_vpa}{wave}",
                "payee_vpa": f"{event.upi_payload.payee_vpa}{wave}",
            }
        )
    return event.model_copy(update=updates)


def _next_timestamp(world: pd.DataFrame) -> datetime:
    if world.empty or "timestamp" not in world:
        return datetime.now(UTC)
    timestamp = pd.Timestamp(world["timestamp"].max()).to_pydatetime()
    return timestamp.astimezone(UTC) + timedelta(minutes=1)


def _deterministic_event_id(config: CrewConfig, timestamp: datetime, index: int) -> UUID:
    material = f"{config.vector_id}|{timestamp.isoformat()}|{index}".encode()
    return UUID(bytes=blake2b(material, digest_size=16).digest(), version=4)

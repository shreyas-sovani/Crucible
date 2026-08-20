"""Validated loader for Crucible's attack-vector catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Vector(BaseModel):
    """One simulated or playbook-only attack vector."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    family: str = Field(min_length=1)
    rail: Literal["card", "upi"]
    status: Literal["simulated", "playbook"]
    genai_telemetry_requirements: tuple[str, ...] = Field(min_length=1)
    mutation_parameters: tuple[str, ...]


def load_ontology(path: str | Path | None = None) -> list[Vector]:
    """Load and validate catalog source, returning all thirty attack vectors."""

    catalog_path = Path(path) if path is not None else _default_catalog_path()
    with catalog_path.open(encoding="utf-8") as catalog_file:
        raw_catalog = yaml.safe_load(catalog_file)

    if not isinstance(raw_catalog, list):
        msg = "Ontology catalog must contain a YAML list."
        raise ValueError(msg)

    return [Vector.model_validate(raw_vector) for raw_vector in raw_catalog]


def _default_catalog_path() -> Path:
    repository_catalog = Path(__file__).resolve().parents[3] / "data" / "ontology.yaml"
    if repository_catalog.is_file():
        return repository_catalog
    return Path(__file__).resolve().parents[1] / "data" / "ontology.yaml"

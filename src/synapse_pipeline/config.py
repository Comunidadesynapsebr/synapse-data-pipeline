from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    raw: dict[str, Any]

    @property
    def project(self) -> dict[str, Any]:
        return self.raw.get("project", {})

    @property
    def collection(self) -> dict[str, Any]:
        return self.raw.get("collection", {})

    @property
    def cleaning(self) -> dict[str, Any]:
        return self.raw.get("cleaning", {})

    @property
    def publishing(self) -> dict[str, Any]:
        return self.raw.get("publishing", {})

    @property
    def hf_token(self) -> str | None:
        env_name = self.publishing.get("hf_token_env", "HF_TOKEN")
        return os.getenv(env_name)


def load_config(path: str | Path) -> Config:
    with Path(path).open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("A configuração deve ser um objeto YAML")
    fmt = raw.get("project", {}).get("output_format", "jsonl")
    if fmt not in {"jsonl", "parquet", "csv", "txt"}:
        raise ValueError(f"Formato não suportado: {fmt}")
    return Config(raw)

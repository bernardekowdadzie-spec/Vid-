"""Loads config.yaml, the skills profile, and the base CV.

All paths in config.yaml are resolved relative to the project root (the
directory containing main.py), so the app works the same regardless of the
current working directory it's launched from.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        example = path.with_name(path.stem + ".example" + path.suffix)
        hint = f" Copy {example.name} to {path.name} first." if example.exists() else ""
        raise ConfigError(f"Missing required file: {path}.{hint}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class SourceConfig:
    key: str
    name: str
    enabled: bool
    listing_url: str
    selectors: dict[str, Any]


@dataclass
class AppConfig:
    raw: dict[str, Any]
    skills_profile: dict[str, Any]
    base_cv: str
    project_root: Path = field(default=PROJECT_ROOT)

    @property
    def wake_phrase(self) -> str:
        return self.raw.get("wake_phrase", "jarvis wake up").lower()

    @property
    def sleep_phrase(self) -> str:
        return self.raw.get("sleep_phrase", "jarvis go to sleep").lower()

    @property
    def assistant_name(self) -> str:
        return self.raw.get("assistant_name", "Javis")

    @property
    def anthropic_model(self) -> str:
        return self.raw.get("anthropic", {}).get("model", "claude-sonnet-5")

    @property
    def anthropic_api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")

    @property
    def minimum_score(self) -> float:
        return float(self.raw.get("matching", {}).get("minimum_score", 0.35))

    @property
    def top_n_per_scan(self) -> int:
        return int(self.raw.get("matching", {}).get("top_n_per_scan", 10))

    def path(self, key: str) -> Path:
        rel = self.raw.get("paths", {}).get(key)
        if rel is None:
            raise ConfigError(f"paths.{key} not set in config.yaml")
        return self.project_root / rel

    def sources(self) -> list[SourceConfig]:
        out = []
        for key, val in self.raw.get("sources", {}).items():
            if not val.get("enabled", True):
                continue
            out.append(
                SourceConfig(
                    key=key,
                    name=val.get("name", key),
                    enabled=True,
                    listing_url=val["listing_url"],
                    selectors=val.get("selectors", {}),
                )
            )
        return out

    def source(self, key: str) -> SourceConfig:
        val = self.raw.get("sources", {}).get(key)
        if val is None:
            raise ConfigError(f"Unknown source '{key}'. Known: {list(self.raw.get('sources', {}))}")
        return SourceConfig(
            key=key,
            name=val.get("name", key),
            enabled=val.get("enabled", True),
            listing_url=val["listing_url"],
            selectors=val.get("selectors", {}),
        )


def load_config(root: Path | None = None) -> AppConfig:
    root = root or PROJECT_ROOT
    raw = _load_yaml(root / "config" / "config.yaml")

    paths = raw.get("paths", {})
    skills_path = root / paths.get("skills_profile", "data/skills_profile.yaml")
    cv_path = root / paths.get("base_cv", "data/base_cv.md")

    skills_profile = _load_yaml(skills_path)

    if not cv_path.exists():
        example = cv_path.with_name(cv_path.stem + ".example" + cv_path.suffix)
        hint = f" Copy {example.name} to {cv_path.name} first." if example.exists() else ""
        raise ConfigError(f"Missing required file: {cv_path}.{hint}")
    base_cv = cv_path.read_text(encoding="utf-8")

    output_dir = root / paths.get("output_dir", "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(raw=raw, skills_profile=skills_profile, base_cv=base_cv, project_root=root)

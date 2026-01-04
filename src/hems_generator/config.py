"""Configuration models for the scenery generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GeneratorConfig:
    """Runtime configuration for batch generation."""

    output_dir: Path
    cache_dir: Path = Path(".cache")
    aoi_radius_m: int = 600
    quality: str = "medium"
    cars_density: float = 0.5
    night_lighting: float = 0.6
    generator_version: str = "0.3.1-campus-parking"

    def ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def ensure_cache_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

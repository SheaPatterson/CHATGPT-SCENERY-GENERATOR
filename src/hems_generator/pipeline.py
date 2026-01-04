"""Pipeline execution for HEMS scenery generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from hems_generator.config import GeneratorConfig
from hems_generator.exporter import SceneryPackage
from hems_generator.utils import ensure_unique_paths, slugify


@dataclass(frozen=True)
class HospitalSite:
    faa_id: str
    name: str


@dataclass(frozen=True)
class PipelineResult:
    package: SceneryPackage
    zip_path: Path


def resolve_sites(faa_ids: Iterable[str], name_map: dict[str, str]) -> List[HospitalSite]:
    sites = []
    for faa_id in faa_ids:
        cleaned = faa_id.strip().upper()
        if not cleaned:
            continue
        name = name_map.get(cleaned, "UNKNOWN")
        sites.append(HospitalSite(faa_id=cleaned, name=slugify(name)))
    return sites


def build_scenery_batch(
    faa_ids: Iterable[str],
    name_map: dict[str, str],
    config: GeneratorConfig,
) -> List[PipelineResult]:
    config.ensure_output_dir()
    sites = resolve_sites(faa_ids, name_map)
    results: List[PipelineResult] = []
    output_paths = []

    for site in sites:
        package = SceneryPackage(site.faa_id, site.name, config.output_dir)
        package.build_skeleton()
        package_name = f"HOSP_{site.faa_id}_{site.name}"
        zip_path = config.output_dir / f"{package_name}.zip"
        output_paths.append(zip_path)
        package.zip_to(zip_path)
        results.append(PipelineResult(package=package, zip_path=zip_path))

    ensure_unique_paths(output_paths)
    return results

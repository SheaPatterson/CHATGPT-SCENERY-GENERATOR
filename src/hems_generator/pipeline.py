"""Pipeline execution for HEMS scenery generation."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians
from pathlib import Path
from typing import Iterable, List

from hems_generator.config import GeneratorConfig
from hems_generator.detection import resolve_height, resolve_helipad_position
from hems_generator.dsf_writer import write_overlay_stub
from hems_generator.exporter import SceneryPackage
from hems_generator.job import HospitalJob, create_default_job
from hems_generator.obj_writer import write_simple_hospital_obj, write_simple_marker_obj
from hems_generator.scene import DrapedPolygon, Scene, SceneLight, SceneObject
from hems_generator.utils import ensure_unique_paths, slugify, write_text


@dataclass(frozen=True)
class HospitalSite:
    faa_id: str
    name: str


@dataclass(frozen=True)
class PipelineResult:
    package: SceneryPackage
    zip_path: Path
    job_path: Path
    scene_path: Path


def resolve_sites(faa_ids: Iterable[str], name_map: dict[str, str]) -> List[HospitalSite]:
    sites = []
    for faa_id in faa_ids:
        cleaned = faa_id.strip().upper()
        if not cleaned:
            continue
        name = name_map.get(cleaned, "UNKNOWN")
        sites.append(HospitalSite(faa_id=cleaned, name=slugify(name)))
    return sites


def _job_path(jobs_dir: Path, site: HospitalSite) -> Path:
    return jobs_dir / f"{site.faa_id}_{site.name}" / "hospital_job.json"


def _build_scene(job: HospitalJob) -> Scene:
    helipad_lat, helipad_lon = resolve_helipad_position(job)
    drape_vertices = _square_around(job.location.lat, job.location.lon, 12.0)
    return Scene(
        objects=[
            SceneObject(
                obj="hospital_0.obj",
                lat=job.location.lat,
                lon=job.location.lon,
                heading=0,
            ),
            SceneObject(
                obj="helipad_marker.obj",
                lat=helipad_lat,
                lon=helipad_lon,
                heading=0,
            ),
        ],
        draped_polygons=[
            DrapedPolygon(name="helipad_markings.pol", vertices=drape_vertices),
        ],
        lights=[
            SceneLight(name="heli_pad_green", lat=helipad_lat, lon=helipad_lon, intensity=1.0),
        ],
    )


def _square_around(lat: float, lon: float, size_m: float) -> list[list[float]]:
    half = size_m / 2
    lat_offset = half / 111_320
    lon_offset = half / (111_320 * cos(radians(lat)) or 1)
    return [
        [lat - lat_offset, lon - lon_offset],
        [lat - lat_offset, lon + lon_offset],
        [lat + lat_offset, lon + lon_offset],
        [lat + lat_offset, lon - lon_offset],
    ]


def build_scenery_batch(
    faa_ids: Iterable[str],
    name_map: dict[str, str],
    coord_map: dict[str, tuple[float, float]],
    config: GeneratorConfig,
    jobs_dir: Path,
) -> List[PipelineResult]:
    config.ensure_output_dir()
    sites = resolve_sites(faa_ids, name_map)
    results: List[PipelineResult] = []
    output_paths = []

    for site in sites:
        job_path = _job_path(jobs_dir, site)
        if job_path.exists():
            job = HospitalJob.load(job_path)
        else:
            lat, lon = coord_map.get(site.faa_id, (0.0, 0.0))
            job = create_default_job(site.faa_id, site.name, lat, lon, config.aoi_radius_m)
            job.save(job_path)
        height_result = resolve_height(job)
        job.hospital.floors = height_result.floors
        job.hospital.height_m = height_result.height_m
        job.save(job_path)

        package = SceneryPackage(site.faa_id, site.name, config.output_dir)
        package.build_skeleton()
        write_text(
            package.scenery_path / "polygons" / "helipad_markings.pol",
            "\n".join(
                [
                    "A",
                    "850",
                    "DRAPED_POLYGON",
                    "",
                    "TEXTURE helipad_markings.png",
                    "SCALE 1.0 1.0",
                    "",
                ]
            ),
        )
        scene = _build_scene(job)
        package.write_scene(scene)
        write_simple_hospital_obj(package.scenery_path / "objects" / "hospital_0.obj")
        write_simple_marker_obj(package.scenery_path / "objects" / "helipad_marker.obj")
        write_overlay_stub(package.scenery_path, scene, job.location.lat, job.location.lon)
        zip_path = config.output_dir / f"HOSP_{site.faa_id}_{site.name}.zip"
        output_paths.append(zip_path)
        package.zip_to(zip_path)
        results.append(
            PipelineResult(
                package=package,
                zip_path=zip_path,
                job_path=job_path,
                scene_path=package.scenery_path / "scene.json",
            )
        )

    ensure_unique_paths(output_paths)
    return results

"""Pipeline execution for HEMS scenery generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha1
from math import cos, radians
from pathlib import Path
from typing import Iterable, List

from hems_generator.config import GeneratorConfig
from hems_generator.detection import resolve_height, resolve_helipad_position
from hems_generator.dsf_writer import tile_for_location, write_overlay_stub
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
    config.ensure_cache_dir()
    _ensure_cache_layers(config.cache_dir)
    write_text(config.output_dir / "generator_version.txt", f"{config.generator_version}\n")
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
        _write_helipad_polygon(package.scenery_path)
        _write_objects(package.scenery_path)

        build_hash = _build_cache_key(job, config.generator_version)
        build_dir = config.cache_dir / "build" / f"build_{build_hash}"
        stage_paths = _stage_paths(build_dir)
        cache_hit = all(path.exists() for path in stage_paths.values())

        if cache_hit:
            _hydrate_from_cache(
                package.scenery_path,
                stage_paths,
                job.location.lat,
                job.location.lon,
            )
        else:
            scene = _build_scene(job)
            package.write_scene(scene)
            dsf_path = write_overlay_stub(
                package.scenery_path,
                scene,
                job.location.lat,
                job.location.lon,
            )
            _persist_cache(
                build_dir,
                scene,
                dsf_path,
                job,
            )

        package_name = f"HOSP_{site.faa_id}_{site.name}"
        zip_path = config.output_dir / f"{package_name}.zip"
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


def _ensure_cache_layers(cache_dir: Path) -> None:
    for layer in ("geo", "elev", "imagery", "build"):
        (cache_dir / layer).mkdir(parents=True, exist_ok=True)


def _build_cache_key(job: HospitalJob, generator_version: str) -> str:
    payload = json.dumps(job.to_dict(), sort_keys=True)
    digest = sha1()
    digest.update(payload.encode("utf-8"))
    digest.update(generator_version.encode("utf-8"))
    return digest.hexdigest()


def _stage_paths(build_dir: Path) -> dict[str, Path]:
    return {
        "scene": build_dir / "scene.json",
        "buildings": build_dir / "buildings.json",
        "parking": build_dir / "parking.json",
        "lights": build_dir / "lights.json",
        "dsf": build_dir / "dsf_stub.txt",
    }


def _persist_cache(build_dir: Path, scene: Scene, dsf_path: Path, job: HospitalJob) -> None:
    build_dir.mkdir(parents=True, exist_ok=True)
    stage_paths = _stage_paths(build_dir)
    write_text(stage_paths["scene"], scene.to_json())
    write_text(stage_paths["dsf"], dsf_path.read_text(encoding="utf-8"))
    write_text(stage_paths["buildings"], json.dumps({"floors": job.hospital.floors}))
    write_text(stage_paths["parking"], json.dumps({"enabled": job.ground.generate_parking}))
    write_text(stage_paths["lights"], json.dumps({"night_strength": job.lighting.night_strength}))


def _hydrate_from_cache(
    scenery_path: Path,
    stage_paths: dict[str, Path],
    lat: float,
    lon: float,
) -> None:
    write_text(scenery_path / "scene.json", stage_paths["scene"].read_text(encoding="utf-8"))
    dsf_tile = tile_for_location(lat, lon)
    dsf_path = dsf_tile.file_path(scenery_path)
    write_text(dsf_path, stage_paths["dsf"].read_text(encoding="utf-8"))


def _write_helipad_polygon(scenery_path: Path) -> None:
    content = "\n".join(
        [
            "A",
            "850",
            "DRAPED_POLYGON",
            "",
            "TEXTURE helipad_markings.png",
            "SCALE 1.0 1.0",
            "",
        ]
    )
    write_text(scenery_path / "polygons" / "helipad_markings.pol", content)


def _write_objects(scenery_path: Path) -> None:
    write_simple_hospital_obj(scenery_path / "objects" / "hospital_0.obj")
    write_simple_marker_obj(scenery_path / "objects" / "helipad_marker.obj")

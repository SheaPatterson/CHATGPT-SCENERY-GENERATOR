"""CLI entrypoint for the HEMS scenery generator."""

from __future__ import annotations

import argparse
import csv
from zipfile import ZipFile
from pathlib import Path
from typing import Iterable

from hems_generator.config import GeneratorConfig
from hems_generator.pipeline import build_scenery_batch
from hems_generator.utils import dated_bulk_name, slugify


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate HEMS hospital scenery packages.")
    parser.add_argument("--ids", help="Comma-separated FAA IDs.")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="CSV with columns: faa_id,name,lat,lon.",
    )
    parser.add_argument("--output", default="output", help="Output directory.")
    parser.add_argument("--jobs-dir", default="output/jobs", help="Job files directory.")
    parser.add_argument("--csv", dest="csv_path", help="CSV with columns: faa_id,name.")
    parser.add_argument("--output", default="output", help="Output directory.")
    parser.add_argument("--aoi-radius", type=int, default=600, help="AOI radius in meters.")
    parser.add_argument("--quality", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--cars-density", type=float, default=0.5)
    parser.add_argument("--night-lighting", type=float, default=0.6)
    return parser.parse_args()


def _parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value.strip() == "":
        return default
    return float(value)


def load_csv(path: Path) -> tuple[list[str], dict[str, str], dict[str, tuple[float, float]]]:
    ids: list[str] = []
    names: dict[str, str] = {}
    coords: dict[str, tuple[float, float]] = {}
def load_csv(path: Path) -> tuple[list[str], dict[str, str]]:
    ids: list[str] = []
    names: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            faa_id = (row.get("faa_id") or "").strip().upper()
            if not faa_id:
                continue
            name = slugify((row.get("name") or "UNKNOWN").strip())
            lat = _parse_float(row.get("lat"))
            lon = _parse_float(row.get("lon"))
            ids.append(faa_id)
            names[faa_id] = name
            coords[faa_id] = (lat, lon)
    return ids, names, coords
            ids.append(faa_id)
            names[faa_id] = name
    return ids, names


def ids_from_arg(ids_arg: str | None) -> Iterable[str]:
    if not ids_arg:
        return []
    return [chunk.strip() for chunk in ids_arg.split(",") if chunk.strip()]


def main() -> int:
    args = parse_args()
    ids = list(ids_from_arg(args.ids))
    names: dict[str, str] = {}
    coords: dict[str, tuple[float, float]] = {}

    if args.csv_path:
        csv_ids, csv_names, csv_coords = load_csv(Path(args.csv_path))
        ids.extend(csv_ids)
        names.update(csv_names)
        coords.update(csv_coords)

    if args.csv_path:
        csv_ids, csv_names = load_csv(Path(args.csv_path))
        ids.extend(csv_ids)
        names.update(csv_names)

    if not ids:
        raise SystemExit("Provide --ids or --csv with FAA IDs.")

    config = GeneratorConfig(
        output_dir=Path(args.output),
        aoi_radius_m=args.aoi_radius,
        quality=args.quality,
        cars_density=args.cars_density,
        night_lighting=args.night_lighting,
    )
    jobs_dir = Path(args.jobs_dir)
    results = build_scenery_batch(ids, names, coords, config, jobs_dir)
    results = build_scenery_batch(ids, names, config)

    bulk_zip = config.output_dir / dated_bulk_name()
    with ZipFile(bulk_zip, "w") as archive:
        for result in results:
            base_dir = result.package.package_dir
            for path in base_dir.rglob("*"):
                archive.write(path, path.relative_to(config.output_dir))
    for result in results:
        print(f"Generated {result.zip_path}")
        print(f"Job file {result.job_path}")
            archive.write(result.zip_path, result.zip_path.name)
    for result in results:
        print(f"Generated {result.zip_path}")

    print(f"Bulk archive placeholder created at {bulk_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

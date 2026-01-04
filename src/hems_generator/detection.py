"""Auto-detection rules for hospitals and helipads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from hems_generator.job import HospitalJob


@dataclass(frozen=True)
class HeightResult:
    floors: int
    height_m: float


def compute_floors_from_area(area_m2: Optional[float]) -> int:
    if not area_m2 or area_m2 <= 0:
        return 4
    floors = round(area_m2 / 1200)
    return max(2, min(8, floors))


def resolve_height(job: HospitalJob) -> HeightResult:
    if isinstance(job.hospital.floors, int):
        floors = job.hospital.floors
    else:
        floors = compute_floors_from_area(job.hospital.area_m2)
    height_m = floors * 3.8
    if isinstance(job.hospital.height_m, (int, float)):
        height_m = float(job.hospital.height_m)
    return HeightResult(floors=floors, height_m=height_m)


def resolve_helipad_position(job: HospitalJob) -> tuple[float, float]:
    if job.helipad.position is not None:
        return job.helipad.position.lat, job.helipad.position.lon
    return job.location.lat, job.location.lon

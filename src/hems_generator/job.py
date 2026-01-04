"""Job file model and persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Location:
    lat: float
    lon: float


@dataclass
class AOI:
    radius_m: int = 600


@dataclass
class HospitalSpec:
    footprint_source: str = "auto"
    footprint_override: Optional[Dict[str, Any]] = None
    height_m: str | float = "auto"
    roof_type: str = "flat"
    floors: str | int = "auto"
    area_m2: Optional[float] = None


@dataclass
class HelipadSpec:
    mode: str = "auto"
    position: Optional[Location] = None
    type: str = "hospital"
    surface: str = "concrete"
    lighting: bool = True


@dataclass
class GroundSpec:
    generate_parking: bool = True
    generate_roads: bool = False
    generate_sidewalks: bool = True
    generate_curbs: bool = True


@dataclass
class PropsSpec:
    cars_density: float = 0.7
    people: bool = False
    fences: bool = True
    trees: bool = True


@dataclass
class LightingSpec:
    night_strength: float = 0.6
    interior_glow: bool = True


@dataclass
class OutputSpec:
    quality: str = "high"
    flatten_helipad: bool = True


@dataclass
class HospitalJob:
    id: str
    name: str
    location: Location
    aoi: AOI
    hospital: HospitalSpec
    helipad: HelipadSpec
    ground: GroundSpec
    props: PropsSpec
    lighting: LightingSpec
    output: OutputSpec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "location": {"lat": self.location.lat, "lon": self.location.lon},
            "aoi": {"radius_m": self.aoi.radius_m},
            "hospital": {
                "footprint_source": self.hospital.footprint_source,
                "footprint_override": self.hospital.footprint_override,
                "height_m": self.hospital.height_m,
                "roof_type": self.hospital.roof_type,
                "floors": self.hospital.floors,
                "area_m2": self.hospital.area_m2,
            },
            "helipad": {
                "mode": self.helipad.mode,
                "position": None
                if self.helipad.position is None
                else {"lat": self.helipad.position.lat, "lon": self.helipad.position.lon},
                "type": self.helipad.type,
                "surface": self.helipad.surface,
                "lighting": self.helipad.lighting,
            },
            "ground": {
                "generate_parking": self.ground.generate_parking,
                "generate_roads": self.ground.generate_roads,
                "generate_sidewalks": self.ground.generate_sidewalks,
                "generate_curbs": self.ground.generate_curbs,
            },
            "props": {
                "cars_density": self.props.cars_density,
                "people": self.props.people,
                "fences": self.props.fences,
                "trees": self.props.trees,
            },
            "lighting": {
                "night_strength": self.lighting.night_strength,
                "interior_glow": self.lighting.interior_glow,
            },
            "output": {
                "quality": self.output.quality,
                "flatten_helipad": self.output.flatten_helipad,
            },
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HospitalJob":
        location = Location(**data["location"])
        helipad_position = data.get("helipad", {}).get("position")
        return cls(
            id=data["id"],
            name=data["name"],
            location=location,
            aoi=AOI(**data.get("aoi", {})),
            hospital=HospitalSpec(**data.get("hospital", {})),
            helipad=HelipadSpec(
                mode=data.get("helipad", {}).get("mode", "auto"),
                position=Location(**helipad_position) if helipad_position else None,
                type=data.get("helipad", {}).get("type", "hospital"),
                surface=data.get("helipad", {}).get("surface", "concrete"),
                lighting=data.get("helipad", {}).get("lighting", True),
            ),
            ground=GroundSpec(**data.get("ground", {})),
            props=PropsSpec(**data.get("props", {})),
            lighting=LightingSpec(**data.get("lighting", {})),
            output=OutputSpec(**data.get("output", {})),
        )

    @classmethod
    def load(cls, path: Path) -> "HospitalJob":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def create_default_job(
    faa_id: str,
    name: str,
    lat: float,
    lon: float,
    aoi_radius: int = 600,
) -> HospitalJob:
    return HospitalJob(
        id=faa_id,
        name=name,
        location=Location(lat=lat, lon=lon),
        aoi=AOI(radius_m=aoi_radius),
        hospital=HospitalSpec(),
        helipad=HelipadSpec(),
        ground=GroundSpec(),
        props=PropsSpec(),
        lighting=LightingSpec(),
        output=OutputSpec(),
    )


def apply_preview_overrides(job: HospitalJob, overrides: Dict[str, Any]) -> HospitalJob:
    if "hospital" in overrides:
        hospital_data = overrides["hospital"]
        for key, value in hospital_data.items():
            setattr(job.hospital, key, value)
    if "helipad" in overrides:
        helipad_data = overrides["helipad"]
        if "position" in helipad_data and helipad_data["position"] is not None:
            position = helipad_data["position"]
            job.helipad.position = Location(lat=position["lat"], lon=position["lon"])
        for key, value in helipad_data.items():
            if key != "position":
                setattr(job.helipad, key, value)
    if "ground" in overrides:
        for key, value in overrides["ground"].items():
            setattr(job.ground, key, value)
    if "props" in overrides:
        for key, value in overrides["props"].items():
            setattr(job.props, key, value)
    if "lighting" in overrides:
        for key, value in overrides["lighting"].items():
            setattr(job.lighting, key, value)
    return job

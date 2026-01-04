"""Scene graph representation for deterministic exports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SceneObject:
    obj: str
    lat: float
    lon: float
    heading: float
    elevation: str = "ground"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "obj": self.obj,
            "lat": self.lat,
            "lon": self.lon,
            "heading": self.heading,
            "elevation": self.elevation,
        }


@dataclass(frozen=True)
class DrapedPolygon:
    name: str
    vertices: List[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "draped_polygon",
            "name": self.name,
            "vertices": self.vertices,
        }


@dataclass(frozen=True)
class SceneLine:
    name: str
    vertices: List[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "line",
            "name": self.name,
            "vertices": self.vertices,
        }


@dataclass(frozen=True)
class SceneLight:
    name: str
    lat: float
    lon: float
    intensity: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "light",
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "intensity": self.intensity,
        }


@dataclass
class Scene:
    objects: List[SceneObject] = field(default_factory=list)
    draped_polygons: List[DrapedPolygon] = field(default_factory=list)
    lines: List[SceneLine] = field(default_factory=list)
    lights: List[SceneLight] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objects": [obj.to_dict() for obj in self.objects],
            "draped_polygons": [poly.to_dict() for poly in self.draped_polygons],
            "lines": [line.to_dict() for line in self.lines],
            "lights": [light.to_dict() for light in self.lights],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

"""Placeholder overlay DSF writer.

This writer emits a human-readable stub aligned with scene graph content.
Binary DSF emission will replace this stub in a future iteration.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from pathlib import Path
from typing import Iterable, Tuple

from hems_generator.scene import Scene


@dataclass(frozen=True)
class DsfTile:
    lat: int
    lon: int

    @property
    def folder_name(self) -> str:
        lat_prefix = "+" if self.lat >= 0 else "-"
        lon_prefix = "+" if self.lon >= 0 else "-"
        return f"{lat_prefix}{abs(self.lat):02d}{lon_prefix}{abs(self.lon):03d}"

    def file_path(self, root: Path) -> Path:
        folder = root / "Earth nav data" / self.folder_name
        return folder / f"{self.folder_name}.dsf"


def tile_for_location(lat: float, lon: float) -> DsfTile:
    return DsfTile(lat=floor(lat), lon=floor(lon))


def _format_vertices(vertices: Iterable[Tuple[float, float]]) -> str:
    return "\n".join(f"  {lat:.6f} {lon:.6f}" for lat, lon in vertices)


def write_overlay_stub(root: Path, scene: Scene, lat: float, lon: float) -> Path:
    tile = tile_for_location(lat, lon)
    dsf_path = tile.file_path(root)
    dsf_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Overlay DSF placeholder (textual stub).",
        "# Objects",
    ]
    for obj in scene.objects:
        lines.append(f"OBJECT {obj.obj} {obj.lat:.6f} {obj.lon:.6f} {obj.heading:.1f}")
    lines.append("# Draped polygons")
    for poly in scene.draped_polygons:
        lines.append(f"POLYGON {poly.name}")
        lines.append(_format_vertices([(v[0], v[1]) for v in poly.vertices]))
    lines.append("# Lines")
    for line in scene.lines:
        lines.append(f"LINE {line.name}")
        lines.append(_format_vertices([(v[0], v[1]) for v in line.vertices]))
    lines.append("# Lights")
    for light in scene.lights:
        lines.append(
            f"LIGHT {light.name} {light.lat:.6f} {light.lon:.6f} {light.intensity:.2f}"
        )
    dsf_path.write_text("\n".join(lines), encoding="utf-8")
    return dsf_path

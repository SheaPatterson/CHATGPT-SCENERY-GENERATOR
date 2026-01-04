"""OBJ8 writer for static scenery objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class ObjMesh:
    vertices: List[Tuple[float, float, float]]
    uvs: List[Tuple[float, float]]
    indices: List[int]


def write_obj8(path: Path, mesh: ObjMesh, texture: str, lit_texture: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "I",
        "800",
        "OBJ",
        "",
        f"TEXTURE {texture}",
        f"TEXTURE_LIT {lit_texture}",
        "",
        "POINT_COUNTS 0 0 0 0",
        "",
    ]
    for (x, y, z), (u, v) in zip(mesh.vertices, mesh.uvs):
        lines.append(f"VT {x:.3f} {y:.3f} {z:.3f} {u:.4f} {v:.4f}")
    lines.append("")
    for idx in mesh.indices:
        lines.append(f"IDX {idx}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def quad_mesh(size: float = 10.0) -> ObjMesh:
    half = size / 2
    vertices = [
        (-half, 0.0, -half),
        (half, 0.0, -half),
        (half, 0.0, half),
        (-half, 0.0, half),
    ]
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    indices = [0, 1, 2, 0, 2, 3]
    return ObjMesh(vertices=vertices, uvs=uvs, indices=indices)


def write_simple_hospital_obj(path: Path, size: float = 30.0) -> None:
    mesh = quad_mesh(size=size)
    write_obj8(path, mesh, "hospital_0.png", "hospital_0_LIT.png")


def write_simple_marker_obj(path: Path, size: float = 6.0) -> None:
    mesh = quad_mesh(size=size)
    write_obj8(path, mesh, "helipad_markings.png", "helipad_markings_LIT.png")

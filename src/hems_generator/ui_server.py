"""Minimal web UI server for the HEMS scenery generator."""

from __future__ import annotations

import argparse
import csv
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from urllib.parse import parse_qs, urlparse

from hems_generator.config import GeneratorConfig
from hems_generator.pipeline import build_scenery_batch

UI_DIR = Path(__file__).parent / "ui"


def _parse_faa_ids(raw: str) -> list[str]:
    separators = [",", "\n", "\t", " "]
    cleaned = raw
    for sep in separators:
        cleaned = cleaned.replace(sep, ",")
    return [item.strip() for item in cleaned.split(",") if item.strip()]


def _parse_csv_payload(data: str) -> Tuple[Dict[str, str], Dict[str, Tuple[float, float]]]:
    name_map: Dict[str, str] = {}
    coord_map: Dict[str, Tuple[float, float]] = {}
    if not data.strip():
        return name_map, coord_map

    reader = csv.DictReader(data.splitlines())
    for row in reader:
        faa_id = (row.get("faa_id") or row.get("id") or "").strip().upper()
        if not faa_id:
            continue
        name = (row.get("name") or "UNKNOWN").strip()
        name_map[faa_id] = name
        lat_value = (row.get("lat") or "").strip()
        lon_value = (row.get("lon") or "").strip()
        if lat_value and lon_value:
            try:
                coord_map[faa_id] = (float(lat_value), float(lon_value))
            except ValueError:
                continue
    return name_map, coord_map


def _safe_resolve(base_dir: Path, target: str) -> Path | None:
    if not target:
        return None
    target_path = Path(target)
    resolved = target_path if target_path.is_absolute() else (base_dir / target_path)
    resolved = resolved.resolve()
    try:
        resolved.relative_to(base_dir.resolve())
    except ValueError:
        return None
    return resolved


class SceneryUIHandler(BaseHTTPRequestHandler):
    server_version = "HEMSUI/0.1"

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_file(UI_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            path = UI_DIR / parsed.path.removeprefix("/static/")
            if path.suffix == ".css":
                self._serve_file(path, "text/css; charset=utf-8")
            elif path.suffix == ".js":
                self._serve_file(path, "application/javascript; charset=utf-8")
            else:
                self._serve_file(path, "application/octet-stream")
            return
        if parsed.path.startswith("/api/download/"):
            query = parse_qs(parsed.query)
            output_dir = query.get("dir", [""])[0]
            file_name = parsed.path.removeprefix("/api/download/")
            self._serve_download(file_name, output_dir)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/api/generate":
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
            return

        faa_ids_raw = str(data.get("faa_ids") or "")
        csv_data = str(data.get("csv_data") or "")
        output_dir = str(data.get("output_dir") or "output")
        jobs_dir = str(data.get("jobs_dir") or "")
        aoi_radius = int(data.get("aoi_radius_m") or 600)

        faa_ids = _parse_faa_ids(faa_ids_raw)
        name_map, coord_map = _parse_csv_payload(csv_data)
        if not faa_ids and not name_map:
            self._send_json(
                {"error": "Provide FAA IDs or a CSV file with faa_id values."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        if not faa_ids:
            faa_ids = list(name_map.keys())

        base_dir = Path.cwd()
        resolved_output_dir = _safe_resolve(base_dir, output_dir)
        if resolved_output_dir is None:
            self._send_json(
                {"error": "Output directory must be inside the current workspace."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        resolved_jobs_dir = _safe_resolve(
            base_dir,
            jobs_dir or str(Path(output_dir) / "jobs"),
        )
        if resolved_jobs_dir is None:
            self._send_json(
                {"error": "Jobs directory must be inside the current workspace."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        config = GeneratorConfig(output_dir=resolved_output_dir, aoi_radius_m=aoi_radius)
        resolved_jobs_dir.mkdir(parents=True, exist_ok=True)
        results = build_scenery_batch(
            faa_ids=faa_ids,
            name_map=name_map,
            coord_map=coord_map,
            config=config,
            jobs_dir=resolved_jobs_dir,
        )

        response = {
            "output_dir": str(resolved_output_dir),
            "results": [
                {
                    "faa_id": result.package.faa_id,
                    "name": result.package.name,
                    "zip_file": result.zip_path.name,
                    "zip_url": f"/api/download/{result.zip_path.name}?dir={resolved_output_dir}",
                    "job_path": str(result.job_path),
                    "scene_path": str(result.scene_path),
                }
                for result in results
            ],
        }
        self._send_json(response)

    def _serve_download(self, file_name: str, output_dir: str) -> None:
        base_dir = Path.cwd()
        resolved_output_dir = _safe_resolve(base_dir, output_dir)
        if resolved_output_dir is None:
            self._send_json(
                {"error": "Invalid download directory."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        file_path = (resolved_output_dir / file_name).resolve()
        try:
            file_path.relative_to(resolved_output_dir)
        except ValueError:
            self._send_json({"error": "Invalid download path."}, status=HTTPStatus.BAD_REQUEST)
            return
        if not file_path.exists():
            self._send_json({"error": "File not found."}, status=HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.send_header("Content-Disposition", f"attachment; filename={file_name}")
        self.end_headers()
        with file_path.open("rb") as handle:
            self.wfile.write(handle.read())

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str, port: int) -> None:
    server_address = (host, port)
    with ThreadingHTTPServer(server_address, SceneryUIHandler) as httpd:
        print(f"HEMS UI available at http://{host}:{port}")
        httpd.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the HEMS UI server.")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host interface to bind (0.0.0.0 for external access).",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()

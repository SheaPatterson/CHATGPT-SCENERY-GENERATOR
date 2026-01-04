# HEMS Hospital Scenery Generator

A local, offline-friendly pipeline that turns FAA IDs into X-Plane 11 hospital scenery packages.

## Features

- Generates one zip per hospital: `output/HOSP_<ID>_<name>.zip`.
- Generates a bulk archive: `output/BULK_<date>.zip`.
- Creates a complete X-Plane 11 scenery folder structure under `Custom Scenery/`.

## Quick start

```bash
python -m hems_generator.cli --ids 1TN4,7NC1 --output output
```

### CSV input

```csv
faa_id,name
1TN4,Regional Medical Center
7NC1,Heliport Hospital
```

```bash
python -m hems_generator.cli --csv hospitals.csv --output output
```

## Roadmap alignment

The core pipeline scaffolding matches the intended steps:

1. Resolve AOI and hospital footprint
2. Generate hospital OBJ (procedural extrude + roof)
3. Ground surfaces (draped polygons + linework)
4. Props placement
5. Night ops tuning (_LIT textures, lights)
6. Export to DSF + package

Each step is currently a placeholder in the export output so the pipeline can be filled in with GIS + meshing logic later.

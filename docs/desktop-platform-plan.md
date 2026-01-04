# Desktop Platform Plan

This document captures the proposed desktop architecture for evolving the local HEMS scenery
pipeline into an Electron-based tool with a headless TypeScript engine and shared types.

## 1) High-level architecture

Single repo, two layers:

```
hospital-scenery-generator/
├── app/        ← Electron UI (TypeScript)
├── engine/     ← Generation engine (TypeScript, headless)
├── shared/     ← Types, schemas, utilities
├── assets/     ← Textures, line defs, pols, light defs
├── output/
├── .cache/
└── package.json
```

Electron talks to the engine via direct imports (no IPC unless needed for isolation).

## 2) Core tech stack

### UI

- **Electron** for the desktop shell.
- **React + Vite** for UI iteration.
- **Map**: MapLibre GL (offline-friendly).
- **State**: React state, optionally Zustand.

### Engine

- **Node 20+**
- **TypeScript**
- **Geometry**: `@turf/*` for buffers/centroids/simplification.
- **Triangulation**: `earcut`.
- **Math**: plain TypeScript (no heavy 3D library required).
- **File I/O**: Node `fs`.
- **Zip**: `adm-zip` or `archiver`.

No Three.js is required for generation output since the engine writes files, not renders meshes.

## 3) Shared types (lock these first)

`shared/types.ts`

```ts
export type LatLon = { lat: number; lon: number };

export type BuildingRole =
  | "main"
  | "clinic"
  | "office"
  | "service"
  | "parking";

export interface HospitalJob {
  id: string;
  name?: string;
  location: LatLon;
  aoi: { radius_m: number };

  campus: {
    buildings?: {
      id: string;
      role: BuildingRole;
    }[];
  };

  helipad: {
    mode: "auto" | "manual";
    position?: LatLon;
  };

  output: {
    quality: "low" | "medium" | "high";
    flatten_helipad: boolean;
  };
}
```

Everything keys off this shared job schema.

## 4) Engine module layout

```
engine/
├── index.ts                ← main entry
├── job/
│   ├── loadJob.ts
│   ├── hashJob.ts
│   └── validateJob.ts
├── geo/
│   ├── osmFetch.ts
│   ├── footprintSelect.ts
│   └── campusCluster.ts
├── geometry/
│   ├── project.ts          ← lat/lon → local meters
│   ├── hospitalMesh.ts     ← main building mesh builder
│   ├── parking.ts
│   └── rooftops.ts
├── textures/
│   ├── atlasBuilder.ts
│   └── litBuilder.ts
├── export/
│   ├── objWriter.ts
│   ├── dsfWriter.ts
│   └── zipPack.ts
├── cache/
│   ├── geoCache.ts
│   ├── elevCache.ts
│   └── buildCache.ts
└── version.ts
```

Each folder is replaceable without touching the others.

## 5) OBJ writer (TypeScript, minimal, fast)

`export/objWriter.ts`

Responsibilities:

- write header
- write vertices + UVs
- write indices

OBJ format is dead simple — don’t overabstract it.

```ts
export function writeOBJ(
  path: string,
  verts: number[],
  uvs: number[],
  indices: number[]
) {
  const out: string[] = [];
  out.push("I", "800", "OBJ");
  out.push("TEXTURE hospital_atlas.png");
  out.push("TEXTURE_LIT hospital_atlas_LIT.png");

  for (let i = 0; i < verts.length; i += 5) {
    out.push(`VT ${verts[i]} ${verts[i + 1]} ${verts[i + 2]} ${verts[i + 3]} ${verts[i + 4]}`);
  }

  for (let i = 0; i < indices.length; i += 3) {
    out.push(`IDX ${indices[i]} ${indices[i + 1]} ${indices[i + 2]}`);
  }

  fs.writeFileSync(path, out.join("\n"));
}
```

## 6) DSF writing

Use an existing JS or Python DSF writer, wrapped from Node if needed.

Realistically:

- Call a small Python helper script via Node for DSF output.
- Pass JSON scene graph data.
- Let Python do the binary DSF write.

DSF specs are painful and existing scripts are proven. This saves weeks of effort.

## 7) Preview UI flow

Components:

- FAA input panel
- Map view
- Detected buildings overlay
- Parking zones overlay
- Helipad marker

Interactions:

- Click building → toggle include
- Click building → assign role
- Drag helipad
- Save → updates job JSON

Preview never touches the build cache.

## 8) One-week execution plan

**Day 1**

- Repo scaffold
- Electron + Vite running
- Shared types defined

**Day 2**

- OSM fetch + geo cache
- Map preview with AOI + buildings

**Day 3**

- Campus clustering + role assignment
- Manual include/exclude in UI

**Day 4**

- Hospital mesh generator (single building)
- OBJ export
- Load into X-Plane manually (test)

**Day 5**

- Parking generation + draped polys
- Linework export

**Day 6**

- Helipad + lights
- Night textures
- Batch job runner

**Day 7**

- Zip packaging
- Cache validation
- 5-hospital batch test

## 9) Final blunt advice

- Do **not** chase photogrammetry.
- Do **not** chase perfect matches.
- Do **not** overbuild UI.
- Build one hospital end-to-end first.
- Fly it in X-Plane every night.
- If it looks good from 500–1000 ft AGL, you win.

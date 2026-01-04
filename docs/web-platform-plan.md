# Web Platform Plan

This document captures the proposed web-based architecture for evolving the local HEMS scenery
pipeline into a hosted tool with real-time OSM data, 3D previews, and downloadable X-Plane
packages.

## 1) Data collection

- **OSM sources**: Use OpenStreetMap for building footprints, roads, parking lots, and helipad
  positions. X-Plane autogen already leverages OSM for roads and water features, but not individual
  buildings (`x-plane.com`, `developer.x-plane.com`).
- **Overpass API**: Query OSM via Overpass and export results as GeoJSON. Overpass Turbo is a
  reference flow for exporting building outlines (`medium.com`).
- **Coordinate normalization**: GeoJSON coordinates are global (lat/lon). Convert to a local
  Cartesian coordinate system before creating 3D geometry to avoid floating-point jitter.
  Recommended libraries: `geolib` (JavaScript) or `pyproj` (Python) (`medium.com`).
- **Elevation data**: Incorporate DEM tiles (e.g., NASA SRTM) to place objects at correct heights
  and support sloped terrain. Candidate tools: `rasterio` or elevation helpers.

## 2) Server-side backend

- **Language/framework**: Python (Flask/FastAPI) or Node.js (Express).
- **Core responsibilities**:
  - Accept FAA IDs or coordinates and query Overpass for OSM data.
  - Convert GeoJSON to local coordinates; classify buildings into roles (main, clinic, office,
    service).
  - Generate procedural OBJ models and DSF overlays (port the existing Python pipeline).
  - Package models, textures, and DSF into a ZIP for download.
- **Caching & storage**:
  - Cache OSM responses for repeated requests.
  - Store generated packages temporarily, or integrate Google Drive for persistence via Drive API.

## 3) Client-side web interface

- **Framework**: React or Vue; Vite recommended for fast iteration.
- **Mapping & preview**:
  - Map: Mapbox GL JS or Leaflet with a tiles provider; render vector overlays and allow draggable
    markers.
  - 3D preview: Three.js to extrude OSM building outlines in-browser.
  - Integration: deck.gl or threebox to synchronize map navigation with 3D models.
- **Workflow features**:
  - Import: paste FAA IDs or upload CSV; show each site with detected footprints; allow role
    reassignment or AOI radius edits.
  - Generation controls: sliders for realism/performance, toggles for lighting/props, overrides
    for building height/style.
  - Progress & downloads: show generation status and provide ZIP or Drive link.
  - Persist settings: local storage or server-side DB.

## 4) Deployment considerations

- **Hosting**: VPS or cloud functions; CPU-intensive generation may require async job queues
  (e.g., Celery + Redis).
- **Authentication**: OAuth2 for Drive uploads.
- **Security**: validate FAA ID inputs; rate-limit Overpass requests.
- **Licensing**: include OSM attribution: "© OpenStreetMap contributors".

## 5) Suggested next steps

1. Stand up a minimal React frontend with a map and FAA ID form; wire to an example Flask API.
2. Expand the backend to fetch live OSM data, classify buildings, and generate real OBJ + DSF.
3. Integrate the Three.js preview for pre-download inspection.
4. Iterate on UI polish and advanced options (photo facades, helipad customization).

# District map data

The map uses public commercial-area geometry from the Seoul Metropolitan Government / Seoul Credit Guarantee Foundation [commercial district analysis map](https://golmok.seoul.go.kr/commercialArea/commercialArea.do). The related [Seoul Open Data catalogue](https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do) describes commercial-area geometry and its coordinate system.

The snapshot was retrieved on November 26, 2026. It covers all 1,587 district codes in the project's 2023–2025 sales archive: 1,047 alley districts, 249 developed districts, 285 traditional markets and six tourist zones. Twenty source codes outside the sales archive were excluded.

- `district_locations.csv`: one `district_code`, `latitude` and `longitude` per district. A point represents the commercial area, not an individual shop.
- `district_boundaries.geojson`: simplified area outlines for the offline map view, with `district_code` and district `type` properties.
- `map_sources.json`: source URLs, response and asset checksums, coverage checks and preparation details.

These are location references from the official map snapshot, not quarter-specific historical boundaries. Coverage does not establish whether a district is currently active. Displayed names come from the selected sales records.

## Preparation

Official polygons were obtained from `https://golmok.seoul.go.kr/gis/wfs/getTrdarFtByKey.json` with POST parameters `gbn` and `tno`. The official map uses `alley`, `devlop`, `tradition` and `tour` for the four district types. Alley polygons were retrieved by district code; the other three types support an empty `tno` for bulk retrieval. No API key was used.

The source uses EPSG:5181. Geometry was converted to WGS84 (EPSG:4326, longitude first) with pyproj. Six invalid source rings were repaired with Shapely; their area changed only by numerical roundoff. Display outlines were simplified with topology preservation, starting at five metres and reducing the tolerance where needed to keep area changes below 1%. Coordinates use a topology-preserving precision grid of six decimal places.

Each location is an interior representative point of the intersection of the original and display polygons, rounded to seven decimal places. Every emitted point was checked against both polygons. All 1,587 display geometries are valid, uniquely keyed and inside Seoul's coordinate range.

pyproj and Shapely were used only to prepare these files. The dashboard reads the bundled files with its existing dependencies and makes no coordinate lookup requests. The street basemap needs internet access; the `Offline outlines` view uses only bundled geometry.

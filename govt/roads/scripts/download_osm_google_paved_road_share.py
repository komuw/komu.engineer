#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "geopandas>=1.0,<2",
#   "numpy>=1.26,<3",
#   "pyogrio>=0.10,<1",
#   "pyproj>=3.6,<4",
#   "requests>=2.31,<3",
#   "shapely>=2.0,<3",
#   "urllib3>=2,<3",
# ]
# ///
"""Calculate 2023 Kenya county paved-road shares from released research data.

The road source is the CC0 Figshare dataset accompanying Zhou, Liu, and Huang
(2024), which classifies all line segments in its January 2023 OpenStreetMap
network as paved or unpaved using OSM labels and Google satellite imagery.
Roads are clipped to pinned 2020 geoBoundaries county polygons, measured
geodesically, and aggregated by surface class.

This is a modelled research estimate, not an official Kenya Roads Board road
inventory. Its denominator is the OSM network represented by the research
dataset, so it is not directly comparable with the reported 2011 government
percentages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pyogrio
import requests
import shapely
from pyproj import Geod, Transformer
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OUTPUT_CSV = "kenya_county_paved_road_share_osm_google_2023.csv"
OUTPUT_METADATA = "kenya_county_paved_road_share_osm_google_2023_metadata.json"
SOURCE_YEAR = 2023

FIGSHARE_ARTICLE_ID = 25_415_206
FIGSHARE_API_URL = f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE_ID}"
FIGSHARE_PAGE = (
    "https://springernature.figshare.com/articles/dataset/"
    "Road_Surface_Type_Dataset_of_Kenya/25415206"
)
FIGSHARE_DOI = "10.6084/m9.figshare.25415206.v1"
ROAD_FILE_ID = 45_061_495
ROAD_ARCHIVE_NAME = "Road Surface Type Dataset of Kenya.zip"
ROAD_ARCHIVE_BYTES = 181_604_451
ROAD_ARCHIVE_MD5 = "3e715936145666869cd55cbcb9c312ec"
ROAD_ARCHIVE_SHA256 = "030e8955bed42635f5bb12edbf818967a6f69a79b367ee64feecb57a5271a357"
ROAD_FEATURE_COUNT = 1_267_818
EXPECTED_SURFACE_COUNTS = {"paved": 253_328, "unpaved": 1_014_490}
ROAD_ARCHIVE_MEMBERS = (
    "final.cpg",
    "final.dbf",
    "final.prj",
    "final.shp",
    "final.shx",
)

ARTICLE_DOI = "10.1038/s41597-024-03158-7"
ARTICLE_URL = f"https://doi.org/{ARTICLE_DOI}"

# Pin the boundary release so reruns do not silently use revised polygons.
BOUNDARY_RELEASE_COMMIT = "9469f09"
BOUNDARY_ARCHIVE_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/"
    f"{BOUNDARY_RELEASE_COMMIT}/releaseData/gbOpen/KEN/ADM1/"
    "geoBoundaries-KEN-ADM1-all.zip"
)
BOUNDARY_ARCHIVE_SHA256 = (
    "61801055936be31ac8655631f998c8b468a9202045466ef0d86e72ebd91edce2"
)
BOUNDARY_GEOJSON_MEMBER = "geoBoundaries-KEN-ADM1.geojson"
BOUNDARY_METADATA_MEMBER = "geoBoundaries-KEN-ADM1-metaData.json"
BOUNDARY_FEATURE_COUNT = 47

# Current official county-code order. Output names match the other normalized
# county files in this repository, allowing a reliable join by county_code.
COUNTIES = (
    (1, "Mombasa"),
    (2, "Kwale"),
    (3, "Kilifi"),
    (4, "Tana River"),
    (5, "Lamu"),
    (6, "Taita Taveta"),
    (7, "Garissa"),
    (8, "Wajir"),
    (9, "Mandera"),
    (10, "Marsabit"),
    (11, "Isiolo"),
    (12, "Meru"),
    (13, "Tharaka Nithi"),
    (14, "Embu"),
    (15, "Kitui"),
    (16, "Machakos"),
    (17, "Makueni"),
    (18, "Nyandarua"),
    (19, "Nyeri"),
    (20, "Kirinyaga"),
    (21, "Muranga"),
    (22, "Kiambu"),
    (23, "Turkana"),
    (24, "West Pokot"),
    (25, "Samburu"),
    (26, "Trans Nzoia"),
    (27, "Uasin Gishu"),
    (28, "Elgeyo Marakwet"),
    (29, "Nandi"),
    (30, "Baringo"),
    (31, "Laikipia"),
    (32, "Nakuru"),
    (33, "Narok"),
    (34, "Kajiado"),
    (35, "Kericho"),
    (36, "Bomet"),
    (37, "Kakamega"),
    (38, "Vihiga"),
    (39, "Bungoma"),
    (40, "Busia"),
    (41, "Siaya"),
    (42, "Kisumu"),
    (43, "Homabay"),
    (44, "Migori"),
    (45, "Kisii"),
    (46, "Nyamira"),
    (47, "Nairobi"),
)

BOUNDARY_NAME_ALIASES = {
    "tharaka": "tharakanithi",
}


class DataError(RuntimeError):
    """Raised when a source or intermediate result fails validation."""


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repository_root,
        help="Directory for generated files (default: repository root)",
    )
    parser.add_argument(
        "--road-archive",
        type=Path,
        help=(
            "Use an already downloaded Figshare ZIP instead of downloading the "
            "181.6 MB source archive; its checksum is still validated"
        ),
    )
    parser.add_argument(
        "--boundary-archive",
        type=Path,
        help=(
            "Use an already downloaded pinned geoBoundaries ZIP instead of "
            "downloading it; its checksum is still validated"
        ),
    )
    return parser.parse_args()


def make_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.75,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "Accept": "application/json, application/zip;q=0.9, */*;q=0.8",
            "User-Agent": "Kenya-county-paved-road-research-estimate/1.0",
        }
    )
    return session


def file_hashes(path: Path) -> dict[str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def sha256(path: Path) -> str:
    return file_hashes(path)["sha256"]


def validate_archive(
    path: Path,
    *,
    expected_sha256: str,
    expected_bytes: int | None = None,
    expected_md5: str | None = None,
) -> dict[str, str]:
    if not path.is_file():
        raise DataError(f"Archive does not exist: {path}")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise DataError(
            f"Unexpected size for {path}: {path.stat().st_size:,} bytes; "
            f"expected {expected_bytes:,}"
        )
    hashes = file_hashes(path)
    if hashes["sha256"] != expected_sha256:
        raise DataError(
            f"SHA-256 mismatch for {path}: {hashes['sha256']} != {expected_sha256}"
        )
    if expected_md5 is not None and hashes["md5"] != expected_md5:
        raise DataError(f"MD5 mismatch for {path}: {hashes['md5']} != {expected_md5}")
    return hashes


def download(session: requests.Session, url: str, destination: Path) -> None:
    print(f"Downloading {url}", flush=True)
    with session.get(url, stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    output.write(block)


def copy_or_download(
    session: requests.Session,
    supplied_path: Path | None,
    url: str,
    destination: Path,
) -> str:
    if supplied_path is None:
        download(session, url, destination)
        return "downloaded"
    source = supplied_path.resolve()
    if not source.is_file():
        raise DataError(f"Supplied archive does not exist: {source}")
    shutil.copyfile(source, destination)
    return "supplied_local_archive"


def extract_members(archive: Path, destination: Path, members: Iterable[str]) -> None:
    with zipfile.ZipFile(archive) as source:
        names = set(source.namelist())
        missing = set(members) - names
        if missing:
            raise DataError(f"{archive} is missing expected members: {sorted(missing)}")
        for member in members:
            # All expected member names are fixed basenames. Do not extract any
            # paths supplied by the archive itself.
            target = destination / Path(member).name
            with source.open(member) as input_file, target.open("wb") as output:
                shutil.copyfileobj(input_file, output)


def get_figshare_metadata(
    session: requests.Session,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = session.get(FIGSHARE_API_URL, timeout=60)
    response.raise_for_status()
    article = response.json()
    if article.get("id") != FIGSHARE_ARTICLE_ID or article.get("doi") != FIGSHARE_DOI:
        raise DataError("Figshare API returned an unexpected article record")
    if article.get("license", {}).get("name") != "CC0":
        raise DataError("The Figshare dataset is no longer labelled CC0")
    matches = [
        item for item in article.get("files", []) if item.get("id") == ROAD_FILE_ID
    ]
    if len(matches) != 1:
        raise DataError(f"Figshare file {ROAD_FILE_ID} was not found exactly once")
    source_file = matches[0]
    expected = {
        "name": ROAD_ARCHIVE_NAME,
        "size": ROAD_ARCHIVE_BYTES,
        "supplied_md5": ROAD_ARCHIVE_MD5,
    }
    for field, expected_value in expected.items():
        if source_file.get(field) != expected_value:
            raise DataError(
                f"Unexpected Figshare file {field}: {source_file.get(field)!r}; "
                f"expected {expected_value!r}"
            )
    return article, source_file


def normalized_name(value: str) -> str:
    key = "".join(character for character in value.casefold() if character.isalnum())
    return BOUNDARY_NAME_ALIASES.get(key, key)


def validate_and_order_boundaries(boundaries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    required_fields = {"shapeName", "geometry"}
    missing = required_fields - set(boundaries.columns)
    if missing:
        raise DataError(f"County boundaries are missing fields: {sorted(missing)}")
    if len(boundaries) != BOUNDARY_FEATURE_COUNT:
        raise DataError(
            f"County boundary file has {len(boundaries)} features; expected 47"
        )
    if boundaries.crs is None:
        raise DataError("County boundary file has no CRS")
    if boundaries.geometry.isna().any() or boundaries.geometry.is_empty.any():
        raise DataError("County boundary file contains missing or empty geometry")
    if not bool(boundaries.geometry.is_valid.all()):
        raise DataError("County boundary file contains invalid geometry")

    by_name: dict[str, int] = {}
    for index, source_name in boundaries["shapeName"].items():
        key = normalized_name(str(source_name))
        if key in by_name:
            raise DataError(f"Duplicate normalized boundary name: {source_name}")
        by_name[key] = index

    expected_keys = {normalized_name(name) for _, name in COUNTIES}
    if set(by_name) != expected_keys:
        raise DataError(
            "County boundary names do not match the expected counties: "
            f"missing={sorted(expected_keys - set(by_name))}, "
            f"unexpected={sorted(set(by_name) - expected_keys)}"
        )

    ordered = boundaries.loc[
        [by_name[normalized_name(name)] for _, name in COUNTIES]
    ].copy()
    ordered["county_code"] = [code for code, _ in COUNTIES]
    ordered["county_name"] = [name for _, name in COUNTIES]
    return ordered.reset_index(drop=True)


def geodesic_length_km(geometries: Any, transformer: Transformer, geod: Geod) -> float:
    """Return geodesic length for line parts, ignoring point-only intersections."""
    parts = shapely.get_parts(geometries)
    while len(parts):
        type_ids = shapely.get_type_id(parts)
        nested = np.isin(type_ids, (5, 7))  # MultiLineString, GeometryCollection
        if not bool(nested.any()):
            break
        parts = np.concatenate((parts[~nested], shapely.get_parts(parts[nested])))

    if not len(parts):
        return 0.0
    type_ids = shapely.get_type_id(parts)
    lines = parts[np.isin(type_ids, (1, 2))]  # LineString, LinearRing
    if not len(lines):
        return 0.0

    coordinates, geometry_indexes = shapely.get_coordinates(lines, return_index=True)
    if len(coordinates) < 2:
        return 0.0
    longitude, latitude = transformer.transform(coordinates[:, 0], coordinates[:, 1])
    adjacent = geometry_indexes[:-1] == geometry_indexes[1:]
    if not bool(adjacent.any()):
        return 0.0
    _, _, distances_m = geod.inv(
        longitude[:-1][adjacent],
        latitude[:-1][adjacent],
        longitude[1:][adjacent],
        latitude[1:][adjacent],
    )
    return float(np.sum(distances_m)) / 1000.0


def aggregate(
    road_path: Path, boundary_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    info = pyogrio.read_info(road_path)
    if info["features"] != ROAD_FEATURE_COUNT:
        raise DataError(
            f"Road dataset has {info['features']:,} features; "
            f"expected {ROAD_FEATURE_COUNT:,}"
        )
    if info["geometry_type"] not in {"LineString", "MultiLineString"}:
        raise DataError(f"Unexpected road geometry type: {info['geometry_type']}")
    if set(info["fields"]) != {"surface", "start_x", "start_y", "end_x", "end_y"}:
        raise DataError(f"Unexpected road fields: {list(info['fields'])}")
    if info["crs"] is None:
        raise DataError("Road dataset has no CRS")

    print(f"Reading {ROAD_FEATURE_COUNT:,} road segments", flush=True)
    roads = pyogrio.read_dataframe(road_path, columns=["surface"])
    if len(roads) != ROAD_FEATURE_COUNT:
        raise DataError("Road feature count changed while reading the source")
    if roads.geometry.isna().any() or roads.geometry.is_empty.any():
        raise DataError("Road dataset contains missing or empty geometry")

    surfaces = roads["surface"].astype(str).str.strip().str.casefold().to_numpy()
    surface_counts = dict(Counter(surfaces))
    if surface_counts != EXPECTED_SURFACE_COUNTS:
        raise DataError(
            f"Unexpected source surface counts: {surface_counts}; "
            f"expected {EXPECTED_SURFACE_COUNTS}"
        )

    boundaries = validate_and_order_boundaries(gpd.read_file(boundary_path))
    boundaries = boundaries.to_crs(roads.crs)
    # Positive-area overlaps would allocate road length to multiple counties.
    boundary_tree = shapely.STRtree(boundaries.geometry.values)
    overlap_pairs = boundary_tree.query(
        boundaries.geometry.values, predicate="overlaps"
    )
    if overlap_pairs.shape[1] != 0:
        raise DataError("County polygons overlap in area")

    road_geometries = roads.geometry.values
    road_tree = shapely.STRtree(road_geometries)
    transformer = Transformer.from_crs(roads.crs, "EPSG:4326", always_xy=True)
    geod = Geod(ellps="WGS84")

    source_lengths = {
        surface: geodesic_length_km(
            road_geometries[surfaces == surface], transformer, geod
        )
        for surface in ("paved", "unpaved")
    }

    output_rows: list[dict[str, Any]] = []
    allocated = {"paved": 0.0, "unpaved": 0.0}
    for boundary in boundaries.itertuples(index=False):
        print(f"Clipping roads to {boundary.county_name}", flush=True)
        indexes = road_tree.query(boundary.geometry, predicate="intersects")
        clipped = shapely.intersection(road_geometries[indexes], boundary.geometry)
        county_surfaces = surfaces[indexes]
        lengths = {
            surface: geodesic_length_km(
                clipped[county_surfaces == surface], transformer, geod
            )
            for surface in ("paved", "unpaved")
        }
        paved = lengths["paved"]
        unpaved = lengths["unpaved"]
        total = paved + unpaved
        if total <= 0:
            raise DataError(f"{boundary.county_name} has no positive road length")
        allocated["paved"] += paved
        allocated["unpaved"] += unpaved
        output_rows.append(
            {
                "county_code": boundary.county_code,
                "county_name": boundary.county_name,
                "paved_road_length_km": f"{paved:.6f}",
                "unpaved_road_length_km": f"{unpaved:.6f}",
                "total_road_length_km": f"{total:.6f}",
                "paved_road_share_percent": f"{paved / total * 100:.4f}",
                "source_year": SOURCE_YEAR,
                "data_status": "modelled_research_estimate",
            }
        )

    if len(output_rows) != 47:
        raise DataError(f"Generated {len(output_rows)} county rows; expected 47")
    if [row["county_code"] for row in output_rows] != list(range(1, 48)):
        raise DataError("Output county codes are not ordered 1 through 47")

    source_total = source_lengths["paved"] + source_lengths["unpaved"]
    allocated_total = allocated["paved"] + allocated["unpaved"]
    coverage_percent = allocated_total / source_total * 100
    if not 99 <= coverage_percent <= 100:
        raise DataError(
            f"County polygons cover only {coverage_percent:.4f}% of source road length"
        )

    details = {
        "source_road_features": len(roads),
        "source_surface_feature_counts": surface_counts,
        "source_network_length_km": {
            "paved": round(source_lengths["paved"], 6),
            "unpaved": round(source_lengths["unpaved"], 6),
            "total": round(source_total, 6),
            "paved_share_percent": round(
                source_lengths["paved"] / source_total * 100, 6
            ),
        },
        "length_allocated_to_counties_km": {
            "paved": round(allocated["paved"], 6),
            "unpaved": round(allocated["unpaved"], 6),
            "total": round(allocated_total, 6),
            "paved_share_percent": round(allocated["paved"] / allocated_total * 100, 6),
        },
        "source_length_allocated_to_counties_percent": round(coverage_percent, 6),
        "source_length_outside_county_polygons_km": round(
            source_total - allocated_total, 6
        ),
        "county_rows": len(output_rows),
    }
    return output_rows, details


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = (
        "county_code",
        "county_name",
        "paved_road_length_km",
        "unpaved_road_length_km",
        "total_road_length_km",
        "paved_road_share_percent",
        "source_year",
        "data_status",
    )
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    session = make_session()
    article, road_file = get_figshare_metadata(session)

    with tempfile.TemporaryDirectory(prefix="kenya-road-surface-") as temporary_dir:
        working_dir = Path(temporary_dir)
        road_archive = working_dir / "roads.zip"
        road_input_mode = copy_or_download(
            session,
            args.road_archive,
            road_file["download_url"],
            road_archive,
        )
        road_hashes = validate_archive(
            road_archive,
            expected_sha256=ROAD_ARCHIVE_SHA256,
            expected_bytes=ROAD_ARCHIVE_BYTES,
            expected_md5=ROAD_ARCHIVE_MD5,
        )

        boundary_archive = working_dir / "boundaries.zip"
        boundary_input_mode = copy_or_download(
            session,
            args.boundary_archive,
            BOUNDARY_ARCHIVE_URL,
            boundary_archive,
        )
        boundary_hashes = validate_archive(
            boundary_archive, expected_sha256=BOUNDARY_ARCHIVE_SHA256
        )

        road_dir = working_dir / "roads"
        road_dir.mkdir()
        extract_members(road_archive, road_dir, ROAD_ARCHIVE_MEMBERS)
        extract_members(
            boundary_archive,
            working_dir,
            (BOUNDARY_GEOJSON_MEMBER, BOUNDARY_METADATA_MEMBER),
        )
        boundary_metadata = json.loads(
            (working_dir / BOUNDARY_METADATA_MEMBER).read_text(encoding="utf-8")
        )
        expected_boundary_metadata = {
            "boundaryID": "KEN-ADM1-32016919",
            "boundaryYear": "2020",
            "boundaryType": "ADM1",
            "boundaryCanonical": "Counties",
            "boundaryLicense": "Public Domain",
            "admUnitCount": "47",
        }
        for field, expected_value in expected_boundary_metadata.items():
            if boundary_metadata.get(field) != expected_value:
                raise DataError(
                    f"Unexpected boundary metadata {field}: "
                    f"{boundary_metadata.get(field)!r}; expected {expected_value!r}"
                )

        rows, details = aggregate(
            road_dir / "final.shp", working_dir / BOUNDARY_GEOJSON_MEMBER
        )

        with tempfile.TemporaryDirectory(
            prefix=".osm-google-road-output-", dir=str(output_dir)
        ) as staging_name:
            staging_dir = Path(staging_name)
            staged_csv = staging_dir / OUTPUT_CSV
            write_csv(staged_csv, rows)

            metadata = {
                "calculated_at_utc": datetime.now(timezone.utc).isoformat(),
                "title": (
                    "Modelled paved-road share of OpenStreetMap road length by "
                    "Kenya county, 2023"
                ),
                "indicator": "Paved roads as a percentage of total road length by county",
                "formula": "paved geodesic line length / (paved + unpaved geodesic line length) * 100",
                "source_year": SOURCE_YEAR,
                "source_vintage_notes": [
                    "The research paper says OSM road data through January 2023 were used.",
                    "The paper labels the imagery Maps Data ©2023, but Google imagery can come from different sensors and acquisition dates.",
                    "The source dataset was published on Figshare on 2024-03-21; the associated paper was published on 2024-04-03.",
                ],
                "official_statistic": False,
                "source_road_dataset": {
                    "title": article.get("title"),
                    "authors": [
                        author.get("full_name") for author in article.get("authors", [])
                    ],
                    "figshare_article_id": FIGSHARE_ARTICLE_ID,
                    "figshare_page": FIGSHARE_PAGE,
                    "figshare_api": FIGSHARE_API_URL,
                    "dataset_doi": FIGSHARE_DOI,
                    "associated_paper": ARTICLE_URL,
                    "associated_paper_doi": ARTICLE_DOI,
                    "published_date": article.get("published_date"),
                    "license_name_reported_by_figshare": article.get("license", {}).get(
                        "name"
                    ),
                    "license_url_reported_by_figshare": article.get("license", {}).get(
                        "url"
                    ),
                    "file_id": ROAD_FILE_ID,
                    "file_name": ROAD_ARCHIVE_NAME,
                    "download_url": road_file.get("download_url"),
                    "input_mode": road_input_mode,
                    "bytes": road_archive.stat().st_size,
                    **road_hashes,
                },
                "county_boundaries": {
                    "provider": "geoBoundaries gbOpen",
                    "release_commit": BOUNDARY_RELEASE_COMMIT,
                    "download_url": BOUNDARY_ARCHIVE_URL,
                    "input_mode": boundary_input_mode,
                    "bytes": boundary_archive.stat().st_size,
                    **boundary_hashes,
                    "metadata": boundary_metadata,
                },
                "processing": [
                    "Validated the pinned archives by byte count and cryptographic checksums.",
                    "Required exactly 1,267,818 source road segments and only paved/unpaved surface values with the expected class counts.",
                    "Matched all 47 boundary polygons to official county codes by normalized county name.",
                    "Reprojected 2020 geoBoundaries polygons to the road source CRS (EPSG:3857).",
                    "Split road geometry at county polygons so cross-county segments contribute only their in-county portions.",
                    "Transformed clipped line vertices to longitude/latitude and measured each edge geodesically on the WGS84 ellipsoid.",
                    "Summed paved and unpaved lengths and calculated paved / (paved + unpaved) * 100 for every county.",
                ],
                "validation": details,
                "caveats": [
                    "This is a modelled research estimate, not an official Kenya Roads Board inventory or statistic.",
                    "The denominator is the complete OSM-derived road network released by this study; it differs from the 2011 government source and KRB RICS, so changes between files must not be interpreted solely as roads being paved or unpaved.",
                    "Surface labels are model predictions informed by OSM and Google satellite imagery, not a field survey. The paper reports precision, recall, and F1 above 0.94 for its method.",
                    "Google satellite imagery was captured by different sensors at different, incompletely documented dates.",
                    "The county output excludes source line portions outside the pinned county polygons; the validation block reports the included percentage and omitted length.",
                    "The paper narrative says the nationwide paved proportion is 30% without publishing component lengths. The explicit geodesic length calculation from its released line file is reported in validation.source_network_length_km and is about 9.93%; this output uses the reproducible line-length definition.",
                ],
                "generated_file": {
                    "name": staged_csv.name,
                    "bytes": staged_csv.stat().st_size,
                    "sha256": sha256(staged_csv),
                },
            }
            staged_metadata = staging_dir / OUTPUT_METADATA
            with staged_metadata.open("w", encoding="utf-8") as output:
                json.dump(metadata, output, ensure_ascii=False, indent=2)
                output.write("\n")

            csv_path = output_dir / OUTPUT_CSV
            metadata_path = output_dir / OUTPUT_METADATA
            os.replace(staged_csv, csv_path)
            os.replace(staged_metadata, metadata_path)

    print(f"Wrote {csv_path}")
    print(f"Wrote {metadata_path}")
    print(
        "Allocated "
        f"{details['source_length_allocated_to_counties_percent']:.4f}% "
        "of source road length to 47 counties"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        DataError,
        OSError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        requests.RequestException,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

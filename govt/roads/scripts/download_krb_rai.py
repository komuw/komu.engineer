#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "requests>=2.31,<3",
#   "urllib3>=2,<3",
# ]
# ///
"""Download and process county Rural Access Index data from the KRB web map.

The KRB site is a MangoMap application. It does not expose a single static CSV
link for these layers, so this script uses the same public JSON endpoints as the
browser map:

1. Read the public map page and discover its internal UUID.
2. Read /maps/<UUID>/map_config and locate the RAI 2018 and RAI 2025 layers.
3. Read each county feature's attributes from get_feature_gid.
4. Read the 2025 county geometry from get_feature_geo_json.
5. Validate and write full CSV, analysis-ready CSV, GeoJSON, and provenance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_MAP_URL = (
    "https://maps.krb.go.ke/kenya-roads-board12769/maps/119381/"
    "7-rural-access-index"
)
EXPECTED_YEARS = ("2018", "2025")
EXPECTED_COUNTY_CODES = list(range(1, 48))
MAP_ID_PATTERN = re.compile(
    r'MangoGis\.MapPresenter"\s*,\s*"([0-9a-fA-F-]{36})"'
)


class DownloadError(RuntimeError):
    """Raised when the portal response is not the expected public data."""


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--map-url",
        default=DEFAULT_MAP_URL,
        help="KRB RAI map URL (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root,
        help="Directory for generated files (default: repository root)",
    )
    parser.add_argument(
        "--geometry-zoom",
        type=int,
        choices=range(0, 21),
        default=20,
        metavar="0..20",
        help="Portal geometry detail level; 20 minimizes generalization",
    )
    parser.add_argument(
        "--skip-geometry",
        action="store_true",
        help="Write CSV files only; do not fetch the 2025 GeoJSON geometry",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="Delay in seconds between feature requests (default: %(default)s)",
    )
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    return args


def make_session(referer: str) -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET", "POST")),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (compatible; KRB-RAI-data-fetch/1.0)",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    return session


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs: Any,
) -> Any:
    headers = kwargs.pop("headers", {})
    headers.setdefault("Accept", "application/json")
    response = session.request(
        method,
        url,
        timeout=kwargs.pop("timeout", 60),
        headers=headers,
        **kwargs,
    )
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise DownloadError(f"Expected JSON from {url}, got {response.headers.get('content-type')}") from exc


def discover_map(session: requests.Session, map_url: str) -> tuple[str, str, dict[str, Any]]:
    page_response = session.get(map_url, timeout=60)
    page_response.raise_for_status()
    match = MAP_ID_PATTERN.search(page_response.text)
    if not match:
        raise DownloadError("Could not find the MangoMap UUID in the KRB map page")

    map_id = match.group(1)
    parts = urlsplit(page_response.url)
    base_url = f"{parts.scheme}://{parts.netloc}"
    config_url = f"{base_url}/maps/{map_id}/map_config"
    config = request_json(session, "GET", config_url)
    return base_url, map_id, config


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def discover_layers(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    layers: dict[str, dict[str, Any]] = {}
    for item in walk_dicts(config.get("map_data", {})):
        name = str(item.get("text", "")).strip()
        match = re.fullmatch(r"RAI\s+(\d{4})", name, flags=re.IGNORECASE)
        if match and item.get("id") and item.get("shape_table"):
            year = match.group(1)
            layers[year] = {
                "name": name,
                "layer_id": item["id"],
                "shape_table": item["shape_table"],
                "value_field": (
                    item.get("children", {}).get("value_field")
                    if isinstance(item.get("children"), dict)
                    else None
                ),
            }

    missing = set(EXPECTED_YEARS) - set(layers)
    if missing:
        raise DownloadError(f"Map configuration is missing RAI layer(s): {sorted(missing)}")
    return {year: layers[year] for year in EXPECTED_YEARS}


def get_feature_count(
    session: requests.Session,
    base_url: str,
    map_id: str,
    layer_id: str,
) -> int:
    url = f"{base_url}/maps/{map_id}/count_features"
    data = request_json(session, "GET", url, params={"layer_id": layer_id})
    return int(data["count"])


def get_attributes(
    session: requests.Session,
    base_url: str,
    map_id: str,
    shape_table: str,
    gid: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    url = f"{base_url}/maps/{map_id}/get_feature_gid"
    data = request_json(
        session,
        "POST",
        url,
        json={"data": {"gid": gid, "shape_table": shape_table}},
    )
    try:
        element = data["element"][0]
        values = element["values"]["not_formated"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DownloadError(f"Unexpected attribute response for gid={gid}") from exc
    return values, element


def get_geometry(
    session: requests.Session,
    base_url: str,
    map_id: str,
    shape_table: str,
    gid: int,
    zoom: int,
) -> dict[str, Any]:
    url = f"{base_url}/maps/{map_id}/get_feature_geo_json"
    geometry = request_json(
        session,
        "GET",
        url,
        params={"shape_table_name": shape_table, "gid": gid, "zoom_level": zoom},
        timeout=120,
    )
    if not isinstance(geometry, dict) or "type" not in geometry or "coordinates" not in geometry:
        raise DownloadError(f"Unexpected geometry response for gid={gid}")
    return geometry


def normalized_name(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def numeric(value: Any) -> float:
    return float(str(value).replace(",", ""))


def typed_properties(
    values: dict[str, Any],
    column_types: dict[str, str],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values.items():
        if value is None or value == "":
            result[key] = None
            continue
        datatype = column_types.get(key, "")
        cleaned = str(value).replace(",", "")
        try:
            if datatype == "bigint":
                result[key] = int(cleaned)
            elif datatype == "double precision":
                result[key] = float(cleaned)
            else:
                result[key] = value
        except ValueError:
            result[key] = value
    return result


def validate_records(records: dict[str, list[dict[str, Any]]]) -> None:
    for year, rows in records.items():
        codes = [int(row["countycode"]) for row in rows]
        names = [str(row["countyname"]) for row in rows]
        if codes != EXPECTED_COUNTY_CODES:
            raise DownloadError(f"{year} county codes are not the expected ordered 1..47: {codes}")
        if len(set(names)) != 47:
            raise DownloadError(f"{year} did not return 47 unique county names")

    for old, new in zip(records["2018"], records["2025"]):
        if old["countycode"] != new["countycode"]:
            raise DownloadError("County codes do not align between the two layers")
        if normalized_name(str(old["countyname"])) != normalized_name(str(new["countyname"])):
            raise DownloadError(
                f"County names do not align: {old['countyname']!r} and {new['countyname']!r}"
            )


def write_full_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_combined_csv(path: Path, records: dict[str, list[dict[str, Any]]]) -> None:
    fields = ("county_code", "county_name", "rai_2018_percent", "rai_2025_percent")
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for old, new in zip(records["2018"], records["2025"]):
            writer.writerow(
                {
                    "county_code": int(new["countycode"]),
                    "county_name": new["countyname"],
                    "rai_2018_percent": int(old["rai_1"]),
                    "rai_2025_percent": int(new["rai_2025"]),
                }
            )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    session = make_session(args.map_url)

    print(f"Discovering map configuration from {args.map_url}")
    base_url, map_id, config = discover_map(session, args.map_url)
    config_url = f"{base_url}/maps/{map_id}/map_config"
    layers = discover_layers(config)

    records: dict[str, list[dict[str, Any]]] = {}
    response_metadata: dict[str, dict[str, Any]] = {}
    for year, layer in layers.items():
        count = get_feature_count(session, base_url, map_id, layer["layer_id"])
        if count != 47:
            raise DownloadError(f"RAI {year} returned {count} features; expected 47 counties")
        print(f"Fetching {count} RAI {year} county records")
        rows: list[dict[str, Any]] = []
        for gid in range(1, count + 1):
            values, element = get_attributes(
                session, base_url, map_id, layer["shape_table"], gid
            )
            rows.append(values)
            response_metadata[year] = element
            time.sleep(args.delay)
        records[year] = rows

    validate_records(records)

    # Validate all attributes before spending time on geometry or touching any
    # existing output files.
    rounding_errors = []
    for row in records["2025"]:
        calculated = numeric(row["rural_popu"]) / numeric(row["rural_po_1"]) * 100
        rounding_errors.append(abs(calculated - numeric(row["rai_2025"])))
    max_rounding_error = max(rounding_errors)
    if max_rounding_error > 0.51:
        raise DownloadError(
            f"2025 RAI population-ratio validation failed ({max_rounding_error:.4f})"
        )

    geojson: dict[str, Any] | None = None
    if not args.skip_geometry:
        column_types = {
            item["column"]: item["datatype"]
            for item in response_metadata["2025"]["collumns_name_and_type"]
        }
        features = []
        print(f"Fetching 47 county geometries at zoom level {args.geometry_zoom}")
        for values in records["2025"]:
            gid = int(values["gid"])
            geometry = get_geometry(
                session,
                base_url,
                map_id,
                layers["2025"]["shape_table"],
                gid,
                args.geometry_zoom,
            )
            features.append(
                {
                    "type": "Feature",
                    "id": gid,
                    "properties": typed_properties(values, column_types),
                    "geometry": geometry,
                }
            )
            time.sleep(args.delay)

        geojson = {
            "type": "FeatureCollection",
            "name": "KRB RAI 2025 by county",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
            },
            "features": features,
        }

    # Stage the complete validated snapshot beside the final files. No existing
    # output is replaced until every new data file and its provenance exist.
    with tempfile.TemporaryDirectory(
        prefix=".krb-rai-output-", dir=str(output_dir)
    ) as temporary_dir:
        staging_dir = Path(temporary_dir)
        staged_generated: list[Path] = []
        for year in EXPECTED_YEARS:
            path = staging_dir / f"krb_rai_{year}_counties_full.csv"
            write_full_csv(path, records[year])
            staged_generated.append(path)

        combined_path = staging_dir / "kenya_county_rural_access_index_2018_2025.csv"
        write_combined_csv(combined_path, records)
        staged_generated.append(combined_path)

        if geojson is not None:
            geojson_path = staging_dir / "krb_rai_2025_counties.geojson"
            with geojson_path.open("w", encoding="utf-8") as output:
                json.dump(geojson, output, ensure_ascii=False, separators=(",", ":"))
                output.write("\n")
            staged_generated.append(geojson_path)

        provenance = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_map_url": args.map_url,
            "source_map_id": map_id,
            "source_map_config_url": config_url,
            "layers": layers,
            "feature_count_per_layer": 47,
            "geometry_zoom": None if args.skip_geometry else args.geometry_zoom,
            "api_endpoints": {
                "count": f"{base_url}/maps/{map_id}/count_features?layer_id=<LAYER_ID>",
                "attributes": f"{base_url}/maps/{map_id}/get_feature_gid",
                "geometry": f"{base_url}/maps/{map_id}/get_feature_geo_json",
            },
            "validation": {
                "county_codes": "ordered integers 1 through 47 in both layers",
                "maximum_2025_rounding_difference_percentage_points": round(
                    max_rounding_error, 10
                ),
            },
            "generated_files": {
                path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
                for path in staged_generated
            },
        }
        staged_provenance_path = staging_dir / "krb_rai_fetch_metadata.json"
        with staged_provenance_path.open("w", encoding="utf-8") as output:
            json.dump(provenance, output, ensure_ascii=False, indent=2)
            output.write("\n")

        generated = []
        for staged_path in [*staged_generated, staged_provenance_path]:
            final_path = output_dir / staged_path.name
            os.replace(staged_path, final_path)
            generated.append(final_path)

    print("Validated 47 unique, ordered counties in both layers.")
    print(f"Maximum 2025 RAI rounding difference: {max_rounding_error:.4f} percentage points")
    print("Generated:")
    for path in generated:
        print(f"  {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DownloadError, requests.RequestException, KeyError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

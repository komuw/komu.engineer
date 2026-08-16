#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "requests>=2.31,<3",
#   "urllib3>=2,<3",
# ]
# ///
"""Download and normalize Kenya's reported 2011 county paved-road shares.

The source is an archived Humanitarian Data Exchange (HDX) dataset reported by
the Government of Kenya's Commission on Revenue Allocation. The source already
reports paved roads as a percentage of total roads; it does not provide the
paved and total lengths from which to recompute the percentages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DATASET_ID = "f94db854-d556-422d-bdcb-30791b679dc9"
RESOURCE_ID = "864c5c54-989f-4d60-95b7-6414e2777c4b"
HDX_API_URL = "https://data.humdata.org/api/3/action/package_show"
OUTPUT_CSV = "kenya_county_paved_road_share_2011.csv"
OUTPUT_METADATA = "kenya_county_paved_road_share_2011_metadata.json"
SOURCE_YEAR = 2011

# Official county code order. Names follow the current RAI layer in this repo so
# the datasets can be joined reliably by county_code.
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

# The archived source uses this spelling; normalize it to the current official
# code/name list above.
SOURCE_NAME_ALIASES = {
    "elgeiyomarakwet": "elgeyomarakwet",
}


class DataError(RuntimeError):
    """Raised when the remote dataset does not match the expected structure."""


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repository_root,
        help="Directory for generated files (default: repository root)",
    )
    return parser.parse_args()


def make_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "Accept": "application/json, text/csv;q=0.9, */*;q=0.8",
            "User-Agent": "Kenya-county-paved-road-share-fetch/1.0",
        }
    )
    return session


def normalize_name(value: str) -> str:
    normalized = "".join(character for character in value.lower() if character.isalnum())
    return SOURCE_NAME_ALIASES.get(normalized, normalized)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def get_dataset_metadata(session: requests.Session) -> dict[str, Any]:
    response = session.get(HDX_API_URL, params={"id": DATASET_ID}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not isinstance(payload.get("result"), dict):
        raise DataError("HDX package_show did not return dataset metadata")
    return payload["result"]


def find_csv_resource(metadata: dict[str, Any]) -> dict[str, Any]:
    for resource in metadata.get("resources", []):
        if resource.get("id") == RESOURCE_ID:
            if str(resource.get("format", "")).upper() != "CSV":
                raise DataError("The expected HDX resource is no longer CSV")
            return resource
    raise DataError(f"HDX resource {RESOURCE_ID} was not found")


def download_source_rows(
    session: requests.Session, resource: dict[str, Any]
) -> list[dict[str, str]]:
    response = session.get(resource["url"], timeout=120)
    response.raise_for_status()
    reader = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
    expected_fields = {
        "Country",
        "Counties",
        "Paved Roads as a % of Total Roads",
    }
    if set(reader.fieldnames or []) != expected_fields:
        raise DataError(f"Unexpected source columns: {reader.fieldnames}")
    return [row for row in reader if any((value or "").strip() for value in row.values())]


def process_rows(
    source_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], float, list[str]]:
    values_by_name: dict[str, str] = {}
    national_average: float | None = None

    for row in source_rows:
        if row["Country"].strip() != "Kenya":
            raise DataError(f"Unexpected country value: {row['Country']!r}")
        source_name = row["Counties"].strip()
        raw_value = row["Paved Roads as a % of Total Roads"].strip()
        if source_name == "National Average":
            national_average = float(raw_value)
            continue
        key = normalize_name(source_name)
        if key in values_by_name:
            raise DataError(f"Duplicate county in source: {source_name}")
        values_by_name[key] = raw_value

    if national_average is None:
        raise DataError("Source does not contain the national average")

    expected_names = {normalize_name(name): name for _, name in COUNTIES}
    expected_keys = set(expected_names)
    actual_keys = set(values_by_name)
    unexpected = actual_keys - expected_keys
    if unexpected:
        raise DataError(f"Unexpected source county names: {sorted(unexpected)}")
    missing_rows = expected_keys - actual_keys
    if missing_rows:
        missing_names = sorted(expected_names[key] for key in missing_rows)
        raise DataError(f"Source is missing county rows: {missing_names}")

    output_rows: list[dict[str, Any]] = []
    missing_counties: list[str] = []
    for county_code, county_name in COUNTIES:
        raw_value = values_by_name.get(normalize_name(county_name), "")
        if raw_value == "":
            paved_percent: float | str = ""
            status = "not_reported_by_source"
            missing_counties.append(county_name)
        else:
            paved_percent = float(raw_value)
            if not 0 <= paved_percent <= 100:
                raise DataError(f"Invalid percentage for {county_name}: {paved_percent}")
            status = "reported"
        output_rows.append(
            {
                "county_code": county_code,
                "county_name": county_name,
                "paved_road_share_percent": paved_percent,
                "data_status": status,
                "source_year": SOURCE_YEAR,
            }
        )

    if len(output_rows) != 47 or [row["county_code"] for row in output_rows] != list(range(1, 48)):
        raise DataError("Output is not the expected ordered 47-county table")
    return output_rows, national_average, missing_counties


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = (
        "county_code",
        "county_name",
        "paved_road_share_percent",
        "data_status",
        "source_year",
    )
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    metadata = get_dataset_metadata(session)
    resource = find_csv_resource(metadata)
    source_rows = download_source_rows(session, resource)
    output_rows, national_average, missing_counties = process_rows(source_rows)

    with tempfile.TemporaryDirectory(
        prefix=".paved-road-output-", dir=str(output_dir)
    ) as temporary_dir:
        staging_dir = Path(temporary_dir)
        staged_csv_path = staging_dir / OUTPUT_CSV
        write_csv(staged_csv_path, output_rows)

        output_metadata = {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "title": metadata.get("title"),
            "dataset_id": DATASET_ID,
            "dataset_page": f"https://data.humdata.org/dataset/{DATASET_ID}",
            "dataset_api": f"{HDX_API_URL}?id={DATASET_ID}",
            "resource_id": RESOURCE_ID,
            "resource_url": resource.get("url"),
            "source_year": SOURCE_YEAR,
            "dataset_date": metadata.get("dataset_date"),
            "dataset_source": metadata.get("dataset_source"),
            "methodology": metadata.get("methodology"),
            "caveats": metadata.get("caveats"),
            "archived": metadata.get("archived"),
            "license_id": metadata.get("license_id"),
            "license_title": metadata.get("license_title"),
            "national_average_percent_reported_by_source": national_average,
            "county_rows": len(output_rows),
            "counties_with_reported_values": len(output_rows) - len(missing_counties),
            "counties_not_reported_by_source": missing_counties,
            "processing": [
                "Removed the national-average row from the county output.",
                "Removed the source's trailing empty row.",
                "Required one source row for every expected county.",
                "Normalized county names and assigned official county codes 1 through 47.",
                "Retained blank source values rather than imputing them: "
                + ", ".join(missing_counties)
                + ".",
                (
                    "Did not recompute percentages because the source does not publish "
                    "component road lengths."
                ),
            ],
            "generated_file": {
                "name": staged_csv_path.name,
                "bytes": staged_csv_path.stat().st_size,
                "sha256": sha256(staged_csv_path),
            },
        }
        staged_metadata_path = staging_dir / OUTPUT_METADATA
        with staged_metadata_path.open("w", encoding="utf-8") as output:
            json.dump(output_metadata, output, ensure_ascii=False, indent=2)
            output.write("\n")

        csv_path = output_dir / OUTPUT_CSV
        metadata_path = output_dir / OUTPUT_METADATA
        os.replace(staged_csv_path, csv_path)
        os.replace(staged_metadata_path, metadata_path)

    print(f"Wrote {csv_path}")
    print(f"Reported county values: {len(output_rows) - len(missing_counties)}/47")
    print(f"Missing in source: {', '.join(missing_counties)}")
    print(f"Source national average: {national_average}%")
    print(f"Wrote {metadata_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DataError, requests.RequestException, KeyError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

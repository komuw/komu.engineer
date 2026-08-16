#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Calculate county paved-road shares from KRB RICS 2023 segment CSV exports.

Obtain authorized CSV exports of all five RICS 2023 layers from KRB's Road
Network Surface Type Map, then pass them to this script in the documented
layer order. The required fields are countycode, countyname, agg_surf_t,
rdlength_1, and the globally unique segment ID iid. KRB's popup identifies
rdlength_1 as length in kilometres.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

OUTPUT_NAME = "kenya_county_paved_road_share_rics_2023.csv"
METADATA_NAME = "kenya_county_paved_road_share_rics_2023_metadata.json"
REQUIRED_FIELDS = {"countycode", "countyname", "agg_surf_t", "rdlength_1", "iid"}
VALID_SURFACES = {"Paved", "Unpaved"}

# Positional inputs must follow this order. The counts are the feature counts in
# the fixed RICS 2023 layers documented by the KRB map and were revalidated on
# 2026-08-16. Requiring each count prevents a partial export that happens to
# contain all 47 counties from being published as a complete result.
SOURCE_LAYERS = (
    ("RICS 2023", 40_757),
    ("RICS 2023 Class D,E,F", 39_615),
    ("RICS 2023 Class G_1", 60_001),
    ("RICS 2023 Class G_2", 60_000),
    ("RICS 2023 Class G_3", 60_400),
)
EXPECTED_TOTAL_ROWS = sum(expected_rows for _, expected_rows in SOURCE_LAYERS)


class CalculationError(RuntimeError):
    """Raised when an input cannot be aggregated without ambiguity."""


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs=len(SOURCE_LAYERS),
        type=Path,
        metavar="CSV",
        help=(
            "the five complete RICS 2023 layer exports, in the order shown "
            "in the README"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repository_root,
        help="Directory for generated files (default: repository root)",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregate(paths: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(paths) != len(SOURCE_LAYERS):
        raise CalculationError(
            f"Expected exactly {len(SOURCE_LAYERS)} layer exports; got {len(paths)}"
        )

    lengths: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: {"Paved": Decimal(0), "Unpaved": Decimal(0)}
    )
    names: dict[int, str] = {}
    counts: dict[int, int] = defaultdict(int)
    seen_ids: set[str] = set()
    input_details = []
    total_rows = 0

    for (layer_name, expected_rows), input_path in zip(SOURCE_LAYERS, paths):
        path = input_path.resolve()
        if not path.is_file():
            raise CalculationError(f"Input for {layer_name} does not exist: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            fieldnames = reader.fieldnames or []
            missing = REQUIRED_FIELDS - set(fieldnames)
            if missing:
                raise CalculationError(
                    f"Input for {layer_name} ({path}) is missing fields: {sorted(missing)}"
                )
            file_rows = 0
            for line_number, row in enumerate(reader, start=2):
                file_rows += 1
                total_rows += 1
                segment_id = (row.get("iid") or "").strip()
                if not segment_id:
                    raise CalculationError(f"{path}:{line_number} has an empty iid")
                if segment_id in seen_ids:
                    raise CalculationError(
                        f"Duplicate segment iid={segment_id!r}; inputs may overlap"
                    )
                seen_ids.add(segment_id)

                try:
                    county_code = int((row["countycode"] or "").strip())
                except ValueError as exc:
                    raise CalculationError(
                        f"{path}:{line_number} has invalid countycode {row['countycode']!r}"
                    ) from exc
                if not 1 <= county_code <= 47:
                    raise CalculationError(
                        f"{path}:{line_number} has countycode outside 1..47: {county_code}"
                    )
                county_name = (row["countyname"] or "").strip()
                if not county_name:
                    raise CalculationError(f"{path}:{line_number} has an empty countyname")
                previous_name = names.setdefault(county_code, county_name)
                if previous_name != county_name:
                    raise CalculationError(
                        f"County code {county_code} has conflicting names: "
                        f"{previous_name!r} and {county_name!r}"
                    )

                surface = (row["agg_surf_t"] or "").strip().title()
                if surface not in VALID_SURFACES:
                    raise CalculationError(
                        f"{path}:{line_number} has unsupported agg_surf_t={surface!r}"
                    )
                try:
                    length = Decimal((row["rdlength_1"] or "").strip())
                except InvalidOperation as exc:
                    raise CalculationError(
                        f"{path}:{line_number} has invalid rdlength_1={row['rdlength_1']!r}"
                    ) from exc
                if not length.is_finite() or length < 0:
                    raise CalculationError(
                        f"{path}:{line_number} has invalid road length {length}"
                    )
                lengths[county_code][surface] += length
                counts[county_code] += 1

        if file_rows != expected_rows:
            raise CalculationError(
                f"Input for {layer_name} has {file_rows:,} rows; "
                f"expected {expected_rows:,}"
            )
        input_details.append(
            {
                "source_layer": layer_name,
                "path": str(path),
                "rows": file_rows,
                "expected_rows": expected_rows,
                "id_field": "iid",
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    if total_rows != EXPECTED_TOTAL_ROWS:
        raise CalculationError(
            f"Inputs contain {total_rows:,} rows in total; "
            f"expected {EXPECTED_TOTAL_ROWS:,}"
        )

    missing_counties = sorted(set(range(1, 48)) - set(lengths))
    if missing_counties:
        raise CalculationError(f"No road segments found for county codes: {missing_counties}")

    output_rows = []
    for county_code in range(1, 48):
        paved = lengths[county_code]["Paved"]
        unpaved = lengths[county_code]["Unpaved"]
        total = paved + unpaved
        if total <= 0:
            raise CalculationError(f"County code {county_code} has no positive road length")
        percentage = paved / total * Decimal(100)
        output_rows.append(
            {
                "county_code": county_code,
                "county_name": names[county_code],
                "paved_road_length_km": f"{paved:.6f}",
                "unpaved_road_length_km": f"{unpaved:.6f}",
                "total_road_length_km": f"{total:.6f}",
                "paved_road_share_percent": f"{percentage:.4f}",
                "segment_count": counts[county_code],
                "source_year": 2023,
            }
        )

    details = {
        "input_files": input_details,
        "input_rows": total_rows,
        "unique_segment_ids": len(seen_ids),
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
        "segment_count",
        "source_year",
    )
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, details = aggregate(args.inputs)

    with tempfile.TemporaryDirectory(
        prefix=".rics-2023-output-", dir=str(output_dir)
    ) as temporary_dir:
        staging_dir = Path(temporary_dir)
        staged_csv_path = staging_dir / OUTPUT_NAME
        write_csv(staged_csv_path, rows)
        metadata = {
            "calculated_at_utc": datetime.now(timezone.utc).isoformat(),
            "indicator": "Paved roads as a percentage of total road length by county",
            "formula": "sum(rdlength_1 where agg_surf_t=Paved) / sum(rdlength_1) * 100",
            "length_field": "rdlength_1",
            "length_unit": "kilometres, as labelled in the KRB map popup",
            "surface_field": "agg_surf_t",
            "included_surface_values": sorted(VALID_SURFACES),
            "segment_id_field": "iid",
            "source_map": (
                "https://maps.krb.go.ke/kenya-roads-board12769/maps/110570/"
                "4-road-network-surface-type-map"
            ),
            "source_layers": [
                {"name": name, "expected_rows": expected_rows}
                for name, expected_rows in SOURCE_LAYERS
            ],
            "completeness_validation": (
                "Exactly five ordered inputs with the documented per-layer row counts."
            ),
            "deduplication": (
                "Fails on duplicate iid values across all five inputs rather than "
                "silently double-counting."
            ),
            **details,
            "generated_file": {
                "name": staged_csv_path.name,
                "bytes": staged_csv_path.stat().st_size,
                "sha256": sha256(staged_csv_path),
            },
        }
        staged_metadata_path = staging_dir / METADATA_NAME
        with staged_metadata_path.open("w", encoding="utf-8") as output:
            json.dump(metadata, output, ensure_ascii=False, indent=2)
            output.write("\n")

        csv_path = output_dir / OUTPUT_NAME
        metadata_path = output_dir / METADATA_NAME
        os.replace(staged_csv_path, csv_path)
        os.replace(staged_metadata_path, metadata_path)

    print(f"Aggregated {details['input_rows']:,} unique road segments across 47 counties")
    print(f"Wrote {csv_path}")
    print(f"Wrote {metadata_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CalculationError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

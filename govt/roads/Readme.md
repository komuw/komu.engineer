# Kenya county road-access and paved-road data

This repository contains:

1. County-level Rural Access Index (RAI) data from the Kenya Roads Board (KRB) map.
2. County paved-road shares reported for 2011 by the Government of Kenya's Commission on Revenue Allocation and archived on the Humanitarian Data Exchange (HDX).
3. Reproducible, self-contained [`uv`](https://docs.astral.sh/uv/guides/scripts/) scripts for fetching, normalizing, validating, and processing the data.
4. A processor for calculating updated paved-road shares from authorized KRB RICS 2023 road-segment CSV exports.

The included files were refreshed on **2026-08-16**.

## Results available now

### Rural Access Index

`kenya_county_rural_access_index_2018_2025.csv` contains the RAI percentages displayed by the KRB portal for all 47 counties in 2018 and 2025.

### Percentage of each county's roads that are paved

`kenya_county_paved_road_share_2011.csv` contains one row for each of the 47 counties and uses this definition:

```text
paved-road share (%) = paved road-network length
                       -------------------------- × 100
                       total road-network length
```

Important limitations:

- The county source is from **2011**, not 2023 or 2025.
- It reports percentages directly; it does not provide paved and total component lengths that would allow an independent recalculation.
- Values are reported for 45 counties. The source leaves **Nairobi** and **Samburu** blank; this repository retains them as missing rather than imputing values.
- The source reports a national average of **13.7%**.
- The source is an archived HDX dataset attributed to the Government of Kenya's Commission on Revenue Allocation. HDX labels it `Public Domain / No restrictions (CC0)`.

The latest KRB Surface Type Map contains the fields required for a newer calculation, but its five 2023 layers contain **260,773 road segments** and public bulk export is not available anonymously. The portal's dataset page redirects to sign-in, and making hundreds of thousands of individual feature requests would be inappropriate. Therefore, this repository does not present the 2011 result as a current KRB RICS 2023 result.

After obtaining authorized KRB CSV exports, use `scripts/calculate_paved_share_from_krb_segments.py` to calculate the current percentages. See [Calculating a 2023 paved-road share](#calculating-a-2023-paved-road-share).

## What the Rural Access Index means

The Rural Access Index is **the percentage of the rural population living within 2 km of an all-season road**. It is Sustainable Development Goal indicator 9.1.1:

```text
RAI (%) = rural population within 2 km of an all-season road
          -------------------------------------------------- × 100
                       total rural population
```

An RAI of 87 means that approximately 87% of rural residents—not 87% of roads or land—live within 2 km of a qualifying road.

Under the official SDG definition, an all-season road is motorable throughout the year by the prevailing means of rural transport. It can be paved or unpaved. Predictable short interruptions during bad weather are permitted, but a road expected to be impassable for a total of seven days or more per year is not considered all-season.

The KRB map says its RAI was prepared using KRB road-network data and population data from the Kenya National Bureau of Statistics (KNBS).

RAI and paved-road share answer different questions:

- **RAI:** What percentage of rural people live near an all-season road?
- **Paved-road share:** What percentage of road length is paved?

## Repository contents

| Path | Description |
|---|---|
| `kenya_county_rural_access_index_2018_2025.csv` | Analysis-ready table with county code, county name, 2018 RAI, and 2025 RAI. |
| `krb_rai_2018_counties_full.csv` | All attributes returned by the KRB portal's `RAI 2018` layer. |
| `krb_rai_2025_counties_full.csv` | All attributes returned by the KRB portal's `RAI 2025` layer. |
| `krb_rai_2025_counties.geojson` | All 2025 attributes and 47 county web-map geometries. |
| `krb_rai_fetch_metadata.json` | RAI fetch time, source URLs, discovered IDs, checksums, and validation results. |
| `kenya_county_paved_road_share_2011.csv` | Normalized 47-county table of reported 2011 paved-road shares. |
| `kenya_county_paved_road_share_2011_metadata.json` | HDX source metadata, license, transformations, checksum, and missing-value notes. |
| `scripts/download_krb_rai.py` | Fetches, processes, and validates KRB RAI attributes and geometry. |
| `scripts/download_county_paved_road_share.py` | Fetches and normalizes the archived 2011 county paved-road shares from HDX. |
| `scripts/calculate_paved_share_from_krb_segments.py` | Calculates county shares from authorized KRB RICS 2023 segment CSV exports. |
| `aa.png` | Screenshot of the KRB RAI map supplied with the original request. |

## Running the self-contained scripts with `uv`

Each script contains a [PEP 723 inline dependency block](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies). There is no `requirements.txt`, project environment, or manual `pip install` step. `uv` creates an isolated environment and installs the declared dependencies automatically.

Install `uv` by following <https://docs.astral.sh/uv/getting-started/installation/>, then run commands from this repository's root.

Refresh the RAI files:

```bash
uv run scripts/download_krb_rai.py
```

Refresh the archived county paved-road-share file:

```bash
uv run scripts/download_county_paved_road_share.py
```

Because the scripts have `uv` shebangs and are executable, on systems supporting `/usr/bin/env -S` they can also be run directly:

```bash
./scripts/download_krb_rai.py
./scripts/download_county_paved_road_share.py
```

Show script-specific options:

```bash
uv run scripts/download_krb_rai.py --help
uv run scripts/download_county_paved_road_share.py --help
uv run scripts/calculate_paved_share_from_krb_segments.py --help
```

Each processor stages a complete, validated output set in a temporary directory before replacing final files. A network or validation failure therefore leaves the existing generated snapshot untouched.

## Fetching the KRB Rural Access Index

Source map:

<https://maps.krb.go.ke/kenya-roads-board12769/maps/119381/7-rural-access-index>

A complete refresh, including detailed 2025 county geometry, is:

```bash
uv run scripts/download_krb_rai.py
```

Write to another directory:

```bash
uv run scripts/download_krb_rai.py --output-dir /path/to/output
```

Run a faster attributes-only refresh:

```bash
uv run scripts/download_krb_rai.py --skip-geometry
```

Important options:

- `--map-url URL`: use another deployment of the RAI map.
- `--output-dir DIR`: change the generated-file directory.
- `--geometry-zoom 0..20`: set the web geometry detail level; default 20.
- `--skip-geometry`: omit GeoJSON geometry requests.
- `--delay SECONDS`: delay between feature requests; default 0.05 seconds.

A complete run makes 47 attribute requests for each of two layers and 47 geometry requests. It retries transient errors and inserts a small delay to avoid unnecessarily loading the portal.

### RAI fetch protocol

The website is a MangoMap application rather than a page with one static CSV link. The script follows the public JSON calls used by the browser map.

#### 1. Discover the map UUID

The script downloads the public map page and reads the UUID passed to `MangoGis.MapPresenter`. At this refresh the UUID was:

```text
13be7704-b7b8-11eb-a5c1-06765ea3034e
```

#### 2. Read the map configuration

```text
GET https://maps.krb.go.ke/maps/<MAP_UUID>/map_config
```

The script recursively finds layer objects named `RAI 2018` and `RAI 2025` and reads their `id` and `shape_table`. Current snapshot identifiers are:

| Layer | Layer ID | Shape table |
|---|---|---|
| RAI 2018 | `1a62ca2c-b869-11eb-b5c6-06765ea3034e` | `shp_24008796_b7b9_11eb_9c46_06765ea3034e` |
| RAI 2025 | `4a4a9540-3d1b-11f0-b229-02af6ed49e2d` | `shp_3f223c40_3d1b_11f0_b229_02af6ed49e2d` |

The identifiers can change if KRB replaces a layer, so the script discovers them every run.

#### 3. Confirm feature counts

```text
GET /maps/<MAP_UUID>/count_features?layer_id=<LAYER_ID>
```

Both layers currently report 47 features.

#### 4. Fetch county attributes

```text
POST /maps/<MAP_UUID>/get_feature_gid
Content-Type: application/json

{"data":{"gid":1,"shape_table":"<SHAPE_TABLE>"}}
```

Current layers use sequential `gid` values 1–47. The script reads `element[0].values.not_formated`, preserves the portal fields in the full CSV files, and validates ordered unique county codes 1–47.

#### 5. Fetch 2025 county geometry

```text
GET /maps/<MAP_UUID>/get_feature_geo_json
    ?shape_table_name=<SHAPE_TABLE>
    &gid=<GID>
    &zoom_level=20
```

The endpoint returns web-display geometry generalized according to `zoom_level`. Level 20 is the map's maximum configured zoom and minimizes generalization. Output coordinates use CRS84 longitude/latitude order. This is not an authoritative legal-boundary dataset.

#### 6. Process and validate

The script:

1. Writes every returned source attribute to each full CSV.
2. Creates the analysis-ready CSV using `rai_1` for 2018 and `rai_2025` for 2025.
3. Validates 47 unique counties with codes 1–47 in both layers.
4. Aligns years by county code and compares normalized county names.
5. Verifies that `rural_popu / rural_po_1 × 100` rounds to the displayed 2025 RAI. The maximum difference in this snapshot is 0.4932 percentage points.
6. Writes source identifiers and SHA-256 hashes to `krb_rai_fetch_metadata.json`.

### RAI source fields and quality notes

Use:

- County code: `countycode`
- County name: `countyname`
- 2018 displayed RAI percentage: `rai_1`
- 2025 displayed RAI percentage: `rai_2025`

The map does not publish a complete data dictionary for its other fields. Full outputs retain portal names rather than replacing them with assumptions.

- The 2025 fields `rural_popu` and `rural_po_1` reproduce `rai_2025` after rounding for every county.
- The 2018 ancillary fields `population`, `ruralpop_2`, and `rai` do not consistently reproduce `rai_1`; use `rai_1` for the displayed 2018 value.
- Units for `area_2km__`, `area_rural`, `shape_area`, and `shape_leng` are not documented on the map.
- Four county labels differ in punctuation or spacing between layers. Records are joined by county code; the combined output uses 2025 labels.
- KRB warns that portal boundaries are not authoritative for boundary delimitation.

## Fetching the reported 2011 paved-road shares

Source dataset:

<https://data.humdata.org/dataset/f94db854-d556-422d-bdcb-30791b679dc9>

Run:

```bash
uv run scripts/download_county_paved_road_share.py
```

The script:

1. Calls HDX's CKAN `package_show` API for dataset `f94db854-d556-422d-bdcb-30791b679dc9`.
2. Locates CSV resource `864c5c54-989f-4d60-95b7-6414e2777c4b` from the API response instead of embedding a temporary signed S3 URL.
3. Downloads the source CSV.
4. Removes the national-average row and trailing empty row from county output.
5. Requires a source row for every expected county, so a truncated download cannot be mistaken for blank source values.
6. Normalizes county spellings and assigns codes 1–47.
7. Preserves source blanks for Nairobi and Samburu with `data_status=not_reported_by_source`.
8. Validates all nonmissing percentages are between 0 and 100.
9. Writes source metadata and a SHA-256 checksum.

No paved or total length fields are present in this source, so the script does not claim to recompute its percentages.

## Calculating a 2023 paved-road share

KRB's [Road Network Surface Type Map](https://maps.krb.go.ke/kenya-roads-board12769/maps/110570/4-road-network-surface-type-map) says its latest data come from RICS 2023. The current map configuration divides the road network into five layers:

| Layer | Feature count at investigation |
|---|---:|
| `RICS 2023` | 40,757 |
| `RICS 2023 Class D,E,F` | 39,615 |
| `RICS 2023 Class G_1` | 60,001 |
| `RICS 2023 Class G_2` | 60,000 |
| `RICS 2023 Class G_3` | 60,400 |
| **Total** | **260,773** |

Each layer exposes these fields needed for aggregation:

- `countycode` and `countyname`
- `agg_surf_t`, categorized by the map as `Paved` or `Unpaved`
- `rdlength_1`, labelled **Length (Km)** in the KRB feature popup
- `iid`, which the processor requires as the common segment identifier across all five exports

Request or download authorized CSV exports of **all five layers** from KRB. Do not omit a partition or combine overlapping exports. Pass exactly five files in the table order shown above; the command below demonstrates the required order:

```bash
uv run scripts/calculate_paved_share_from_krb_segments.py \
  /path/to/rics-2023.csv \
  /path/to/rics-2023-class-def.csv \
  /path/to/rics-2023-class-g1.csv \
  /path/to/rics-2023-class-g2.csv \
  /path/to/rics-2023-class-g3.csv
```

The processor calculates, for each county:

```text
paved_road_length_km   = Σ rdlength_1 where agg_surf_t = Paved
unpaved_road_length_km = Σ rdlength_1 where agg_surf_t = Unpaved
total_road_length_km   = paved_road_length_km + unpaved_road_length_km

paved_road_share_percent = paved_road_length_km
                            --------------------- × 100
                            total_road_length_km
```

It streams the CSV files, uses decimal arithmetic, and validates all of the following before publishing a result:

- Exactly five input files are supplied in the documented layer order.
- Each file has the corresponding feature count shown in the table, for 260,773 segments in total.
- All 47 counties are present.
- Surface values are only `Paved` or `Unpaved`.
- Every row has an `iid`, and no `iid` occurs more than once across the five inputs.

If KRB revises one of the fixed RICS 2023 layers and its feature count changes, the processor fails closed so the expected counts can be reviewed rather than silently accepting a partial export. It produces:

- `kenya_county_paved_road_share_rics_2023.csv`
- `kenya_county_paved_road_share_rics_2023_metadata.json`

Those files are intentionally not present yet because authorized raw RICS 2023 exports are not in this repository.

## Paved-road share versus a paved-road-only RAI

The World Bank/International Road Federation indicator [`IS.ROD.PAVE.ZS`](https://api.worldbank.org/v2/indicator/IS.ROD.PAVE.ZS?format=json) is **Roads, paved (% of total roads)**. It measures network length, not population access.

A paved-road-only population-access index would instead be:

```text
paved-road-only RAI (%) = rural population within 2 km of a paved road
                          -------------------------------------------- × 100
                                  total rural population
```

There is no direct globally standardized SDG counterpart to RAI that requires paving. Calculating this custom indicator requires paved road geometry, gridded rural population, a rural/urban mask, county boundaries, a suitable projected CRS for a 2 km buffer, and population-weighted zonal aggregation. County RAI percentages and paved-road shares alone are insufficient.

## Sources

- KRB RAI map: <https://maps.krb.go.ke/kenya-roads-board12769/maps/119381/7-rural-access-index>
- KRB map portal and disclaimer: <https://maps.krb.go.ke/kenya-roads-board12769/maps>
- KRB Surface Type Map: <https://maps.krb.go.ke/kenya-roads-board12769/maps/110570/4-road-network-surface-type-map>
- HDX 2011 county paved-road shares: <https://data.humdata.org/dataset/f94db854-d556-422d-bdcb-30791b679dc9>
- World Bank RAI overview: <https://datacatalog.worldbank.org/search/dataset/0038250/rural-access-index-rai>
- Official SDG 9.1.1 metadata: <https://unstats.un.org/sdgs/metadata/files/Metadata-09-01-01.pdf>
- World Bank paved-road indicator metadata: <https://api.worldbank.org/v2/indicator/IS.ROD.PAVE.ZS?format=json>
- `uv` script documentation: <https://docs.astral.sh/uv/guides/scripts/>

## Rights and reuse

### KRB-derived files

The KRB portal identifies its content and data as KRB property and states that reproduction or transfer requires prior written consent. It requires attribution to **Kenya Roads Board** and limits reuse under its terms. Review the current portal terms and obtain required permission before publishing, transferring, or commercially using KRB-derived files. This repository does not grant a separate license to KRB data.

### Archived paved-road-share file

HDX identifies the 2011 Commission on Revenue Allocation dataset as `Public Domain / No restrictions (CC0)`. Consult the current HDX metadata record before redistribution.

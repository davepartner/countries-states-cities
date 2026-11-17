# Subsetting reference

`tools/subset.py` slices the canonical `data/` down to the exact levels and
geography an application needs, then emits it in the requested formats.

```
python3 tools/subset.py DATA_DIR OUT_DIR [options]
```

## Flags

| Flag | Values | Effect |
|------|--------|--------|
| `--scope` | `countries`, `countries,states`, `countries,states,counties`, `countries,states,counties,cities`, `all` | Which levels to include. Cascading: parents are included automatically (requesting `cities` always brings `states` and `countries`). |
| `--region` | `Asia`, `Europe`, `Africa`, `Americas`, `Oceania`, `Polar` (repeatable / comma-separated) | Keep only countries in those continents. |
| `--country` | ISO2 codes (`US`, `CA`, `NG`) | Keep only those countries (and everything under them). |
| `--state` | `COUNTRY:STATE` pairs (`US:CA`, `US:NY`, `FR:75`) | Keep only those states; implies their countries; filters cities/counties/postcodes to them. |
| `--format` | `json`, `csv`, `sql`, `xml`, `yml`, `geojson`, `mongodb`, `parquet` (repeatable; default `json`) | Output formats. |
| `--sql-dialect` | `mysql`, `postgresql`, `sqlite`, `sqlserver` (repeatable; default `postgresql`) | SQL dialect, for `--format sql`. |

All filters are **conjunctive** (intersection): a country must pass every
filter you give to be kept.

## The scope ladder

| Scope | Tables emitted | Use case |
|---|---|---|
| `countries` | countries (+ regions/subregions) | country dropdown, ISO code table |
| `countries,states` | + states | country → state cascade |
| `countries,states,counties` | + counties | country → state → county |
| `countries,states,counties,cities` | + cities | full place lookup, city search |
| `all` | + postcodes | address / postcode reference |

`regions` (6 continents) and `subregions` (22) are always included alongside
countries as reference tables.

## Consistency guarantee

The slice is **always internally consistent**:

- Every `country_code` points at an included country.
- Every `state_code` points at an included state (except cross-region counties,
  which legitimately have no single state).
- Every `county_code` / `parent_code` reference resolves — cross-referenced
  records (e.g. a New Zealand district council spanning two regions) are pulled
  back in automatically even if their own state was filtered out.

So you can load the SQL, wire the JSON, or build the dropdowns without chasing
dangling references.

## Examples

```bash
# 1. Just countries (JSON)
python3 tools/subset.py data out --scope countries

# 2. European countries + states (JSON)
python3 tools/subset.py data out --scope countries,states --region Europe

# 3. Cities in California + New York (JSON)
python3 tools/subset.py data out --scope countries,states,cities --state US:CA,US:NY

# 4. Cities in Nigeria and Ghana (CSV)
python3 tools/subset.py data out --scope countries,states,cities --country NG,GH --format csv

# 5. Full geography + postcodes for Germany, as PostgreSQL
python3 tools/subset.py data out --scope all --country DE --format sql --sql-dialect postgresql

# 6. African countries only, as a map
python3 tools/subset.py data out --scope countries --region Africa --format geojson

# 7. Everything (identical to tools/export.py)
python3 tools/subset.py data out --scope all
```

## Reading the summary

The tool prints a per-table row count at the end — use it to sanity-check the
slice before integrating (e.g. a `--country NG` slice should show `countries: 1`).

## Whole-world export

When no geography filter is wanted, `tools/export.py data OUT` produces every
format for the full dataset (it is equivalent to `subset.py --scope all` with no
filters).

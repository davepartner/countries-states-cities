# Countries · States · Cities

A clean, natural-key dataset of the world's administrative geography —
**countries, states, counties, cities, and postcodes** — shipped as an
**AI-agent skill** that slices it to exactly what an app needs, in a dozen
formats, with a single-file Python tool and no database or third-party
runtime.

It is a derivative of the
[Countries States Cities Database](https://github.com/dr5hn/countries-states-cities-database)
(dr5hn), reworked with a natural-key data model. See [Attribution](#attribution).

## As an AI-agent skill

`SKILL.md` teaches an agent to implement country/state/city data into any app,
with granular selection:

- **only countries** — `--scope countries`
- **countries + states** — `--scope countries,states`
- **cities in selected states or countries** — `--state US:CA,US:NY` / `--country NG`
- **countries in a continent** — `--region Africa`
- **everything** — `--scope all`

```bash
python3 tools/subset.py data OUT --scope countries,states,cities --country NG --format sql --sql-dialect postgresql
```

The slice is always internally consistent (parents and cross-referenced
counties are pulled in automatically). Full reference: [`references/subsetting.md`](references/subsetting.md),
integration recipes: [`references/integration.md`](references/integration.md).

## Data at a glance

| Dataset | Records |
|---|---|
| Regions | 6 |
| Subregions | 22 |
| Countries | 250 |
| States / regions / municipalities | 5,327 |
| Counties | 14,058 |
| Cities / towns / districts | 171,338 |
| Postcodes | 728,545 (117 countries) |

Country names in **19 languages**, IANA timezones, ISO 3166-1 and ISO 3166-2
codes, native-script names, and Wikidata QIDs.

## What's different from upstream

1. **Natural keys instead of surrogate IDs** — records are keyed by
   `(country_code, code)`: ISO codes and Wikidata QIDs / stable slugs, not
   auto-increment integers.
2. **`type` is no longer a grab-bag** — split into orthogonal `kind`
   (settlement / division / subdivision / historic) + a small `type` enum, with
   the local term in `type_local`.
3. **Volatile fields are honest** — `gdp` removed; `population` always carries
   a `population_year`; `phone` is a list.
4. **One runtime, no MySQL/PHP/Node** — a single Python script regenerates
   every format from `data/`.
5. **Self-consistent docs** — the numbers above are computed from `data/`.

See [SCHEMA.md](SCHEMA.md) for the full field reference.

## Formats

`tools/export.py` (whole world) and `tools/subset.py` (any slice) produce:
JSON, CSV, SQL (MySQL / PostgreSQL / SQLite / SQL Server), XML, YAML, GeoJSON,
MongoDB (NDJSON), and Parquet.

## Quick start

```bash
# whole world, every format
python3 tools/export.py data dist

# a slice (e.g. European countries + states, as CSV)
python3 tools/subset.py data out --scope countries,states --region Europe --format csv

# integrity checks
python3 tools/validate.py data
```

Python 3.10+, standard library only (`pyarrow` optional, for Parquet).

## Data model

- **countries** — `code` = ISO 3166-1 alpha-2.
- **states** — `(country_code, code)`; `code` = ISO 3166-2 suffix.
- **counties** — units between state and municipality (US counties, French
  arrondissements, German Kreise, …).
- **cities** — municipalities, settlements, and parts of them.
- **postcodes** — flat reference table.

See [SCHEMA.md](SCHEMA.md) and [`references/data-model.md`](references/data-model.md).

## Contributing

Edit the canonical JSON under `data/` with natural keys only. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License & attribution

Licensed under the **Open Database License (ODbL) v1.0** ([LICENSE](LICENSE)).
Attribution is required; derivatives share-alike.

This dataset is a derivative of the **Countries States Cities Database**
(<https://github.com/dr5hn/countries-states-cities-database>), © dr5hn,
ODbL v1.0. Per-record source credits (GeoNames, OpenStreetMap, Wikidata, and
~90 national registers) are preserved in
[LICENSES/SOURCES.txt](LICENSES/SOURCES.txt) and must travel with any copy —
see [NOTICE.md](NOTICE.md).

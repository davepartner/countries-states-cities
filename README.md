# Countries · States · Counties · Cities

A clean, natural-key dataset of the world's administrative geography:
**countries, states, counties, cities, and postcodes**, in a dozen formats,
with a single-file Python exporter and no database or third-party runtime
required.

This is a derivative of the
[Countries States Cities Database](https://github.com/dr5hn/countries-states-cities-database)
(dr5hn), reworked with a natural-key data model. See [Attribution](#attribution).

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

Also included: country names in **19 languages**, IANA timezones, ISO 3166-1
and ISO 3166-2 codes, native-script names, and Wikidata QIDs.

## What's different here

This fork fixes several structural problems in the upstream dataset:

1. **Natural keys instead of surrogate IDs.** Records are identified by
   `(country_code, code)` — ISO codes and Wikidata QIDs / stable slugs — not
   auto-increment integers. Contributors never copy opaque `state_id` /
   `country_id` numbers. See [SCHEMA.md](SCHEMA.md).
2. **`type` is no longer a grab-bag.** The old 35-value `type` field mixed
   "what a place is" with "what admin role it fills". It is now two orthogonal
   fields — `kind` (settlement / division / subdivision / historic) and `type`
   (a small enum) — with the local term in `type_local`.
3. **Volatile fields are honest.** `gdp` is removed. `population` always carries
   a `population_year`; a `null` year means "unknown", not "silently stale".
   `phone` is a list so multi-code countries are representable.
4. **One runtime, no MySQL/PHP/Node.** A single Python script regenerates every
   format from the canonical `data/`. No database, no submodules.
5. **Self-consistent docs.** The numbers above are computed from `data/`, so the
   README and the data cannot drift apart.

## Formats

`tools/export.py` produces, from `data/`:

| Format | Contents |
|---|---|
| `json/` | combined `world.json` + one file per table |
| `csv/` | flat CSV per table |
| `sql/` | schema + data for MySQL, PostgreSQL, SQLite, SQL Server |
| `xml/` | per-table XML |
| `yml/` | per-table YAML |
| `geojson/` | GeoJSON `FeatureCollection` (Point features) |
| `mongodb/` | NDJSON for `mongoimport` |
| `parquet/` | columnar Parquet (requires `pyarrow`) |

The `dist/` directory is generated and git-ignored; only the canonical
`data/` is committed.

## Quick start

**Use the canonical JSON directly** (no build step):

```bash
curl -LO https://raw.githubusercontent.com/davepartner/countries-states-cities/main/data/countries.json
```

**Regenerate every format locally** (Python 3.10+, standard library only):

```bash
python3 tools/export.py data dist          # all formats
python3 tools/export.py data dist          # then inspect dist/
```

**Validate integrity** (uniqueness of keys, foreign-key referential integrity):

```bash
python3 tools/validate.py data
```

**Add Parquet support:**

```bash
pip install pyarrow
```

## Data model

- **countries** — `code` = ISO 3166-1 alpha-2.
- **states** — `(country_code, code)`; `code` = ISO 3166-2 suffix (or a
  documented local code, with the ISO code in `iso3166_2`).
- **counties** — units between the state and the municipality (US counties,
  French arrondissements, German Kreise, …).
- **cities** — municipalities, settlements, and parts of them.
- **postcodes** — flat reference table keyed by `(country_code, state_code,
  code, locality_name)`.

Full field reference and the `kind`/`type` taxonomy: [SCHEMA.md](SCHEMA.md).

## Contributing

Add or correct a record by editing the canonical JSON under `data/` with
natural keys only — `country_code` + `code` + `name` + coordinates. No IDs.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License & attribution

Licensed under the **Open Database License (ODbL) v1.0** (see
[LICENSE](LICENSE)). Attribution is required; derivatives must be shared under
the same license.

This dataset is a derivative of the **Countries States Cities Database**
(<https://github.com/dr5hn/countries-states-cities-database>), © dr5hn,
licensed ODbL v1.0. The per-record source credits and licence notices
(GeoNames, OpenStreetMap, Wikidata, and ~90 national registers) are preserved
in [LICENSES/SOURCES.txt](LICENSES/SOURCES.txt) and must travel with any copy
of the data — see [NOTICE.md](NOTICE.md).

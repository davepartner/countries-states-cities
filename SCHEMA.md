# Schema

This document is the authoritative description of the dataset's data model.

The dataset describes the world's administrative geography as **six datasets**,
each identified by **natural keys** (ISO codes and stable place identifiers)
rather than opaque surrogate integers:

| Dataset     | Key                                                        |
|-------------|------------------------------------------------------------|
| `regions`   | `name`                                                     |
| `subregions`| `name`                                                     |
| `countries` | `code` (ISO 3166-1 alpha-2)                                |
| `states`    | `(country_code, code)` (ISO 3166-2 subdivision code)       |
| `counties`  | `(country_code, code)`                                     |
| `cities`    | `(country_code, code)`                                     |
| `postcodes` | *(flat reference table — see below)*                       |

Every entity is reached through its `country_code` plus its own `code`. There
are no auto-increment IDs anywhere in the canonical data, and a contributor
never has to discover or copy a numeric ID.

## Identity model

### `code`

`code` is a stable identifier, unique within its country (for `countries`, it
is unique globally):

- **countries** — the ISO 3166-1 alpha-2 code (`US`, `FR`, …).
- **states** — the ISO 3166-2 subdivision code suffix (`CA`, `BDS`, …). Where
  a country uses a non-ISO local code (e.g. the French overseas *départements*
  use INSEE codes such as `971`), that local code is used and the ISO 3166-2
  code is recorded separately in `iso3166_2`.
- **counties** and **cities** — no ISO standard exists at this level, so `code`
  is the record's **Wikidata QID** when it has a unique one (e.g. `Q62` for
  San Francisco), otherwise a **stable slug** of the name. When a name repeats
  within a country, the slug is disambiguated with a short hash of the
  coordinates (e.g. `springfield-3f9a1c`).

Because `code` is unique within its country, a record is always identified by
`(country_code, code)`. Cross-region counties (a New Zealand district council
spanning two regions) carry a null `state_code` and still resolve cleanly.

### Foreign keys

All relationships use natural keys:

| Field           | References                          | Nullable |
|-----------------|-------------------------------------|----------|
| `country_code`  | `countries.code`                    | no       |
| `state_code`    | `states.code` (same country)        | yes      |
| `county_code`   | `counties.code` (same country)      | yes      |
| `parent_code`   | parent in the same dataset, same country | yes  |
| `city_code`     | `cities.code` (postcodes → city)    | yes      |
| `region` / `subregion` | `regions.name` / `subregions.name` | yes |

## The `kind` / `type` / `type_local` taxonomy

The upstream dataset's `type` field conflated two unrelated questions — *what a
place is* (`city`, `town`, `village`) and *what administrative role it plays*
(`county`, `prefecture`, `adm1`…`adm5`). These are now **two orthogonal
fields**:

- **`kind`** — what the record represents (5 values):

  | `kind`       | meaning                                                  |
  |--------------|----------------------------------------------------------|
  | `settlement` | a populated place (city, town, village, locality, seat)  |
  | `division`   | a territorial administrative unit (municipality, county) |
  | `subdivision`| a part of a settlement (neighbourhood, section, barrio)  |
  | `historic`   | an abandoned, destroyed, historical or religious place   |
  | `other`      | unclassified                                             |

- **`type`** — the standard-English class (a small enum):

  `city`, `town`, `village`, `locality`, `municipality`, `district`,
  `section`, `county`, `province`, `region`, `other`

- **`type_local`** — the official local designation in the country's own
  language (`commune`, `Gemeinde`, `municipio`, `barangay`, …). Free text.

The migration from the legacy `type` values to `(kind, type)` is deterministic
and documented in `tools/convert.py` (see `TYPE_MAP`). Two known, documented
limitations remain:

1. `municipality` is classified `division` (a territory). In some countries a
   municipality is also a populated place in its own right (a French *commune*);
   downstream consumers who want settlements should include `kind = division`
   where a country's municipalities are coextensive with their towns.
2. The legacy `adm1`…`adm5` values (seats of an N-th-order division) are
   classified `settlement`/`city`, with the depth recorded in `level`.

### Filtering to genuine settlements

Because `kind` is orthogonal, the old 15-value exclusion list collapses to:

```sql
SELECT * FROM cities WHERE kind IN ('settlement', 'subdivision');
```

## Volatile fields

`population` is always accompanied by `population_year`. A `null`
`population_year` means the year was not recorded upstream — it is *explicitly
unknown*, not silently ambiguous. `gdp` has been removed: it was stale,
largely null, and out of scope for a geographic dataset.

`phone` (countries) is a list, not a scalar, so countries with multiple
international dialling codes are representable.

## Field reference

### countries

| field | type | notes |
|-------|------|-------|
| `code` | string | ISO 3166-1 alpha-2, primary key |
| `name` | string | English name |
| `iso3` | string | ISO 3166-1 alpha-3 |
| `numeric_code` | string | ISO 3166-1 numeric |
| `phone` | string[] | international dialling code(s) |
| `capital` | string | |
| `currency` | object | `{code, name, symbol}` |
| `tld` | string | |
| `native` | string | name in a native script |
| `population` | integer | |
| `population_year` | integer | year of `population`, or null |
| `area_sq_km` | number | |
| `region` / `subregion` | string | natural key into `regions` / `subregions` |
| `nationality` | string | |
| `postal_code_format` / `postal_code_regex` | string | |
| `timezones` | array | IANA timezones |
| `translations` | object | name in 19 languages |
| `latitude` / `longitude` | string | decimal degrees |
| `emoji` / `emojiU` | string | |
| `wikiDataId` | string | Wikidata QID |

### states

`country_code`, `code`, `name`, `type`, `type_local`, `level`,
`parent_code`, `iso3166_2`, `fips_code`, `native`, `population`,
`population_year`, `latitude`, `longitude`, `timezone`, `translations`,
`wikiDataId`.

### counties

`country_code`, `state_code`, `code`, `name`, `type`, `type_local`, `level`,
`parent_code`, `native`, `population`, `population_year`, `latitude`,
`longitude`, `timezone`, `translations`, `wikiDataId`, `states`
(list of state codes for cross-region counties).

### cities

`country_code`, `state_code`, `code`, `county_code`, `name`, `kind`, `type`,
`type_local`, `level`, `parent_code`, `native`, `population`,
`population_year`, `latitude`, `longitude`, `timezone`, `translations`,
`wikiDataId`.

### postcodes

`country_code`, `state_code`, `code` (the postal code), `locality_name`,
`type`, `latitude`, `longitude`, `source`, `wikiDataId`, `city_code`.

Postcodes are a flat reference table: a postal code is not globally unique, so
the table has no primary key. A postcode row is identified by the combination
`(country_code, state_code, code, locality_name)`.

## Rebuilding

The canonical data lives under `data/`. Every other format is generated from it
by `tools/export.py` — a single Python script, no database or external runtime:

```bash
python3 tools/export.py data dist        # JSON, CSV, SQL×4, XML, YAML, GeoJSON, MongoDB, Parquet
python3 tools/validate.py data           # integrity checks (uniqueness + foreign keys)
```

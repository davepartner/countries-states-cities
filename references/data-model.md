# Data model

Concise summary — the full, authoritative spec is in [`SCHEMA.md`](../SCHEMA.md).

## Six datasets, natural keys

| Dataset | Key | Example |
|---|---|---|
| `regions` | `name` | `Asia` |
| `subregions` | `name` | `Southern Asia` |
| `countries` | `code` (ISO 3166-1 alpha-2) | `US` |
| `states` | `(country_code, code)` (ISO 3166-2) | `US` / `CA` |
| `counties` | `(country_code, code)` | `US` / `Q108053` |
| `cities` | `(country_code, code)` | `US` / `Q62` (San Francisco) |
| `postcodes` | *(flat — no PK)* | `US` / `94103` |

No auto-increment IDs. `code` for a city/county is the record's Wikidata QID
when unique, otherwise a stable slug of the name (coordinate-hashed on
collision).

## Foreign keys (all natural)

`country_code` → countries · `state_code` → states · `county_code` → counties ·
`parent_code` → same-dataset parent · `city_code` (postcodes) → cities ·
`region`/`subregion` (countries) → regions/subregions.

## `kind` vs `type` vs `type_local`

- **`kind`** — what the record *is*: `settlement`, `division`, `subdivision`,
  `historic`, `other`.
- **`type`** — standard-English class: `city`, `town`, `village`, `locality`,
  `municipality`, `district`, `section`, `county`, `province`, `region`, `other`.
- **`type_local`** — the local official designation (`commune`, `Gemeinde`,
  `barangay`).

Filter to settlements with `kind IN ('settlement','subdivision')`.

## Volatile fields

`population` is paired with `population_year` (null = unknown). `gdp` is
removed. `phone` is a list.

## Field reference

| Dataset | Fields |
|---|---|
| countries | `code`, `name`, `iso3`, `numeric_code`, `phone[]`, `capital`, `currency{code,name,symbol}`, `tld`, `native`, `population`, `population_year`, `area_sq_km`, `region`, `subregion`, `nationality`, `postal_code_format`, `postal_code_regex`, `timezones[]`, `translations{}`, `latitude`, `longitude`, `emoji`, `emojiU`, `wikiDataId` |
| states | `country_code`, `code`, `name`, `type`, `type_local`, `level`, `parent_code`, `iso3166_2`, `fips_code`, `native`, `population`, `population_year`, `latitude`, `longitude`, `timezone`, `translations{}`, `wikiDataId` |
| counties | `country_code`, `state_code`, `code`, `name`, `type`, `type_local`, `level`, `parent_code`, `native`, `population`, `population_year`, `latitude`, `longitude`, `timezone`, `translations{}`, `wikiDataId`, `states[]` |
| cities | `country_code`, `state_code`, `code`, `county_code`, `name`, `kind`, `type`, `type_local`, `level`, `parent_code`, `native`, `population`, `population_year`, `latitude`, `longitude`, `timezone`, `translations{}`, `wikiDataId` |
| postcodes | `country_code`, `state_code`, `code`, `locality_name`, `type`, `latitude`, `longitude`, `source`, `wikiDataId`, `city_code` |

Country names are available in 19 languages via `translations`.

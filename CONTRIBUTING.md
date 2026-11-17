# Contributing

Thanks for helping keep this dataset accurate. Contributions are edits to the
canonical JSON under [`data/`](data/) using **natural keys only** — no numeric
IDs, no auto-generated fields.

## Adding or correcting a city

Edit `data/cities/<COUNTRY_CODE>.json` and add a record with only these
fields:

```json
{
    "country_code": "US",
    "state_code": "CA",
    "code": null,
    "name": "New Town",
    "kind": "settlement",
    "type": "town",
    "type_local": null,
    "latitude": "34.12345000",
    "longitude": "-118.12345000",
    "timezone": "America/Los_Angeles",
    "wikiDataId": "Q123456"
}
```

- **`code`** is omitted (or `null`) for new records — it is derived
  automatically: the Wikidata QID when you supply a unique one, otherwise a
  stable slug of the name.
- Required for a new city: `country_code`, `state_code`, `name`, `latitude`,
  `longitude`. Everything else is optional.
- Never add `id`, `created_at`, `updated_at`, `flag`, or any numeric `*_id`
  field — they do not exist in this model.

## Adding or correcting a state

Edit `data/states.json`:

```json
{
    "country_code": "US",
    "code": "XX",
    "name": "New State",
    "type": "state",
    "level": 1
}
```

## Adding or correcting a country

Edit `data/countries.json`:

```json
{
    "code": "XX",
    "name": "Example",
    "iso3": "XXX",
    "numeric_code": "999",
    "phone": ["999"],
    "population": 123456,
    "population_year": 2025
}
```

## Rules

1. **Always include a source.** Points and names must come from an openly
   licensed source (Wikidata CC0, GeoNames CC BY 4.0, OpenStreetMap ODbL, or an
   official register under an open licence). Note the source in your PR.
2. **Match the existing shape.** Look at neighbouring records in the same file
   and follow the field conventions in [SCHEMA.md](SCHEMA.md).
3. **Keep `population_year` honest.** Only set `population` with a year you can
   cite; otherwise leave both null.
4. **Run the validator before you commit:**

   ```bash
   python3 tools/validate.py data
   ```

## After you edit

Open a pull request. CI (and the validator) will confirm the keys are unique
and the foreign keys resolve.

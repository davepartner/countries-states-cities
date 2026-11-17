# Integration reference

Recipes for wiring a generated slice into common stacks. `OUT/` below means the
directory you passed to `tools/subset.py`.

## PostgreSQL / MySQL / SQLite / SQL Server

```bash
python3 tools/subset.py data OUT --scope countries,states,cities --country NG \
    --format sql --sql-dialect postgresql
```

`OUT/sql/postgresql/` contains `schema.sql` (CREATE TABLE + indexes) and
`data.sql` (batched INSERTs). Load in dependency order (already ordered):

```bash
# PostgreSQL
psql "$DATABASE_URL" -f OUT/sql/postgresql/schema.sql
psql "$DATABASE_URL" -f OUT/sql/postgresql/data.sql

# MySQL
mysql -u USER -p DB < OUT/sql/mysql/schema.sql
mysql -u USER -p DB < OUT/sql/mysql/data.sql

# SQLite
sqlite3 app.db < OUT/sql/sqlite/schema.sql
sqlite3 app.db < OUT/sql/sqlite/data.sql
```

Table names: `countries`, `states`, `counties`, `cities`, `postcodes`. Primary
keys are natural composites (`countries.code`; `states (country_code, code)`;
`cities (country_code, code)`). Nested fields (`translations`, `timezones`,
`phone`, `currency`) are stored as JSON text columns.

**Cascading query (country → state → city):**

```sql
-- states of a country
SELECT * FROM states WHERE country_code = 'US' ORDER BY name;
-- cities of a state
SELECT * FROM cities WHERE country_code = 'US' AND state_code = 'CA'
  AND kind IN ('settlement','subdivision') ORDER BY population DESC NULLS LAST;
```

## JSON (static serving / frontend import)

```bash
python3 tools/subset.py data OUT --scope countries,states,cities --country NG
```

`OUT/json/` gives `countries.json`, `states.json`, `cities.json`, plus a
`world.json` that nests them. Serve the files or import them:

```js
import countries from './out/json/countries.json';
import states    from './out/json/states.json';
import cities    from './out/json/cities.json';

// states of a country
const usStates = states.filter(s => s.country_code === 'US');
// cities of a state
const caCities = cities.filter(c => c.country_code === 'US' && c.state_code === 'CA');
```

## Cascading country → state → city selectors

Take `--scope countries,states,cities`. Render the first dropdown from
`countries`, the second from `states.filter(s => s.country_code === selected)`,
the third from `cities.filter(c => c.state_code === selected)`. Because the
slice is FK-consistent, every state resolves to an included country and every
city to an included state.

## CSV / spreadsheet import

```bash
python3 tools/subset.py data OUT --scope countries,states --region Europe --format csv
```

`OUT/csv/countries.csv`, `states.csv`, etc. Nested objects are JSON-encoded
strings in a single column.

## GeoJSON / maps

```bash
python3 tools/subset.py data OUT --scope countries --region Africa --format geojson
```

`OUT/geojson/countries.geojson` is a `FeatureCollection` of Points (one feature
per record, coordinates from `latitude`/`longitude`).

## MongoDB

```bash
python3 tools/subset.py data OUT --scope all --country NG --format mongodb
```

`OUT/mongodb/*.ndjson` — import with `mongoimport --collection cities --file
OUT/mongodb/cities.ndjson`.

## Caveats

- **Attribution.** ODbL requires it. Ship `NOTICE.md` and `LICENSES/` next to
  the data, and credit the Countries States Cities Database.
- **Coordinates are centroids** (approx.), stored with 8-decimal precision —
  suitable for maps and distance sorting, not cadastral accuracy.
- **`population`** is only as fresh as `population_year`; treat `null` year as
  "unknown".
- **`kind`** distinguishes settlements from administrative divisions: filter
  `kind IN ('settlement','subdivision')` for "places", or keep `kind =
  'division'` for municipalities/counties. See `references/data-model.md`.

#!/usr/bin/env python3
"""
Slice the canonical dataset down to exactly what an application needs, then
emit it in the requested formats.

Selection axes (all optional; combine freely):

  --scope  LEVELS      which levels to include (cascading; parents included)
                       countries | countries,states | countries,states,counties |
                       countries,states,counties,cities | all (adds postcodes)
  --region NAMES       restrict countries to continents (Asia, Europe, Africa,
                       Americas, Oceania, Polar)
  --country CODES      restrict to ISO2 country codes (US,CA,MX)
  --state   SPEC       restrict to (country:state) pairs (US:CA,US:NY,FR:75)

  --format  FMT        json,csv,sql,xml,yml,geojson,mongodb,parquet (repeatable)
  --sql-dialect D      mysql,postgresql,sqlite,sqlserver (for --format sql)

Examples:

  # Only countries, as JSON
  python3 tools/subset.py data out --scope countries

  # Countries + states for Europe only
  python3 tools/subset.py data out --scope countries,states --region Europe

  # Cities (with their states/countries) for California and New York
  python3 tools/subset.py data out --scope countries,states,cities --state US:CA,US:NY

  # Everything for Nigeria, as PostgreSQL
  python3 tools/subset.py data out --scope all --country NG --format sql --sql-dialect postgresql

The result is always internally consistent: every foreign key in the slice
resolves (cross-referenced parents are pulled back in automatically).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export  # noqa: E402


ALL_TABLES = ["countries", "states", "counties", "cities", "postcodes"]
SCOPE_DEPS = {
    "postcodes": {"countries"},
    "cities": {"countries", "states"},
    "counties": {"countries", "states"},
    "states": {"countries"},
    "countries": set(),
}


def resolve_tables(scope):
    """Return the ordered list of tables implied by a scope string."""
    if scope is None or scope.strip().lower() == "all":
        requested = set(ALL_TABLES)
    else:
        requested = {p.strip().lower() for p in scope.split(",") if p.strip()}
        unknown = requested - set(ALL_TABLES)
        if unknown:
            raise SystemExit(f"unknown scope level(s): {sorted(unknown)}")

    # close over parent dependencies
    closed = set(requested)
    for level in list(requested):
        closed |= SCOPE_DEPS[level]
    closed |= {"countries"}  # countries always present
    return [t for t in ALL_TABLES if t in closed]


def apply_filters(data, regions=None, countries=None, states=None):
    countries_recs = data["countries"]

    if regions:
        rset = {r.strip().lower() for r in regions}
        countries_recs = [c for c in countries_recs if (c.get("region") or "").lower() in rset]

    if countries:
        cset = {c.strip().upper() for c in countries}
        countries_recs = [c for c in countries_recs if c["code"] in cset]

    # parse "US:CA,US:NY,FR:75" -> {country: set(state)}
    state_filter = None
    if states:
        state_filter = {}
        for spec in states:
            if ":" not in spec:
                raise SystemExit(f"invalid --state value {spec!r}; use COUNTRY:STATE")
            cc, st = spec.split(":", 1)
            state_filter.setdefault(cc.strip().upper(), set()).add(st.strip().upper())
        # a state selection implies its countries
        countries_recs = [c for c in countries_recs if c["code"] in state_filter]

    ccodes = {c["code"] for c in countries_recs}

    states_recs = [s for s in data["states"] if s["country_code"] in ccodes]
    if state_filter:
        states_recs = [s for s in states_recs if s["code"] in state_filter.get(s["country_code"], set())]
    state_keys = {(s["country_code"], s["code"]) for s in states_recs}

    counties_recs = [c for c in data["counties"] if c["country_code"] in ccodes]
    if state_filter:
        counties_recs = [c for c in counties_recs
                         if c["state_code"] is None or (c["country_code"], c["state_code"]) in state_keys]

    cities_recs = [c for c in data["cities"] if c["country_code"] in ccodes]
    if state_filter:
        cities_recs = [c for c in cities_recs if c["state_code"] in state_filter.get(c["country_code"], set())]

    postcodes_recs = [p for p in data["postcodes"] if p["country_code"] in ccodes]
    if state_filter:
        postcodes_recs = [p for p in postcodes_recs
                          if p["state_code"] in state_filter.get(p["country_code"], set())]

    return {
        "regions": data["regions"],
        "subregions": data["subregions"],
        "countries": countries_recs,
        "states": states_recs,
        "counties": counties_recs,
        "cities": cities_recs,
        "postcodes": postcodes_recs,
    }


def referential_closure(filtered, full):
    """
    Pull back any parent/county referenced by a kept record so the slice is
    self-contained (no dangling foreign keys). Cross-region counties referenced
    by a kept city are re-included even though their own state was filtered out.
    """
    state_keys = {(r["country_code"], r["code"]) for r in filtered["states"]}
    county_keys = {(r["country_code"], r["code"]) for r in filtered["counties"]}
    city_keys = {(r["country_code"], r["code"]) for r in filtered["cities"]}

    need_county = {(r["country_code"], r["county_code"]) for r in filtered["cities"] if r.get("county_code")}
    need_city = {(r["country_code"], r["parent_code"]) for r in filtered["cities"] if r.get("parent_code")}
    need_state = {(r["country_code"], r["parent_code"]) for r in filtered["states"] if r.get("parent_code")}
    need_county |= {(r["country_code"], r["parent_code"]) for r in filtered["counties"] if r.get("parent_code")}

    missing_county = need_county - county_keys
    if missing_county:
        bykey = {(c["country_code"], c["code"]): c for c in full["counties"]}
        filtered["counties"] = filtered["counties"] + [bykey[k] for k in missing_county if k in bykey]

    missing_city = need_city - city_keys
    if missing_city:
        bykey = {(c["country_code"], c["code"]): c for c in full["cities"]}
        filtered["cities"] = filtered["cities"] + [bykey[k] for k in missing_city if k in bykey]

    missing_state = need_state - state_keys
    if missing_state:
        bykey = {(s["country_code"], s["code"]): s for s in full["states"]}
        filtered["states"] = filtered["states"] + [bykey[k] for k in missing_state if k in bykey]

    return filtered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="path to data/ directory")
    ap.add_argument("dst", help="directory to write the slice into")
    ap.add_argument("--scope", default="all", help="levels to include (default: all)")
    ap.add_argument("--region", action="append", help="continent(s), repeatable or comma-separated")
    ap.add_argument("--country", action="append", help="ISO2 country code(s), repeatable or comma-separated")
    ap.add_argument("--state", action="append", help="COUNTRY:STATE pair(s), repeatable or comma-separated")
    ap.add_argument("--format", action="append", dest="formats",
                    choices=["json", "csv", "sql", "xml", "yml", "geojson", "mongodb", "parquet"],
                    help="output format (repeatable; default json)")
    ap.add_argument("--sql-dialect", action="append", dest="sql_dialects",
                    choices=["mysql", "postgresql", "sqlite", "sqlserver"],
                    help="SQL dialect (repeatable; default postgresql)")
    args = ap.parse_args()

    def split_multi(vals):
        out = []
        for v in vals or []:
            out += [x.strip() for x in v.split(",") if x.strip()]
        return out

    regions = split_multi(args.region)
    countries = split_multi(args.country)
    states = split_multi(args.state)
    formats = set(args.formats) if args.formats else {"json"}
    dialects = args.sql_dialects or ["postgresql"]

    data = export.load_data(args.data)
    filtered = apply_filters(data, regions, countries, states)

    # referential closure over kept records
    filtered = referential_closure(filtered, data)

    tables = resolve_tables(args.scope)
    # only emit tables that still have content (a slice may have no postcodes)
    tables = [t for t in tables if filtered.get(t)]
    # always keep regions/subregions references when countries present
    emit_tables = ["regions", "subregions"] + tables

    export.emit(filtered, args.dst, tables=emit_tables, formats=formats, sql_dialects=dialects)

    print()
    print("slice summary:")
    for t in emit_tables:
        print(f"  {t}: {len(filtered[t])}")


if __name__ == "__main__":
    main()

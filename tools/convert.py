#!/usr/bin/env python3
"""
One-time migrator from the upstream Countries-States-Cities `contributions/`
JSON (surrogate numeric keys) into this repository's canonical `data/`
layout (natural keys).

This script exists so the migration is reproducible and auditable. The
canonical source of truth for this repo is `data/`, not `contributions/`.

Usage:
    python3 tools/convert.py /path/to/upstream/contributions data/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter


# --------------------------------------------------------------------------- #
# Normalized place taxonomy
#
# The upstream `type` field conflated two orthogonal ideas: what a place *is*
# (city, town, village) and what administrative *role* it fills (adm1..adm5,
# county, prefecture, …). We split them:
#
#   kind  -> settlement | division | subdivision | historic | other
#   type  -> a small, standard-English enum (see SCHEMA.md)
#   type_local -> free-text local designation (unchanged from upstream)
# --------------------------------------------------------------------------- #

# legacy `type` value -> (kind, normalized_type)
TYPE_MAP = {
    "city": ("settlement", "city"),
    "cities": ("settlement", "city"),
    "town": ("settlement", "town"),
    "township": ("settlement", "town"),
    "settlement": ("settlement", "town"),
    "village": ("settlement", "village"),
    "locality": ("settlement", "locality"),
    "subdistrict": ("settlement", "locality"),
    "capital": ("settlement", "city"),
    "gov_seat": ("settlement", "city"),
    # adm1..adm5 are "a real city/town that is also the seat of an N-th-order
    # division" per upstream's own docs. We treat them as settlements and fold
    # the depth into `level`, which is already present.
    "adm1": ("settlement", "city"),
    "adm2": ("settlement", "city"),
    "adm3": ("settlement", "city"),
    "adm4": ("settlement", "city"),
    "adm5": ("settlement", "city"),
    "section": ("subdivision", "section"),
    "municipality": ("division", "municipality"),
    "special municipality": ("division", "municipality"),
    "district": ("division", "district"),
    "borough": ("division", "district"),
    "county": ("division", "county"),
    "prefecture": ("division", "district"),
    "regency": ("division", "district"),
    "banner": ("division", "district"),
    "parish": ("division", "district"),
    "province": ("division", "province"),
    "oblast": ("division", "province"),
    "region": ("division", "region"),
    "area": ("division", "region"),
    "administrative zone": ("division", "region"),
    "abandoned": ("historic", "other"),
    "historical": ("historic", "other"),
    "destroyed": ("historic", "other"),
    "historical_capital": ("historic", "other"),
    "religious": ("historic", "other"),
}


def classify(legacy_type: str | None):
    """Return (kind, type) for a legacy `type` string."""
    if not legacy_type:
        return ("other", "other")
    return TYPE_MAP.get(legacy_type, ("other", "other"))


# --------------------------------------------------------------------------- #
# Identifier helpers
# --------------------------------------------------------------------------- #

def slugify(name: str) -> str:
    """Deterministic ASCII slug of a place name."""
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unnamed"


def coord_hash(lat, lon) -> str:
    digest = hashlib.md5(f"{lat}|{lon}".encode()).hexdigest()
    return digest[:6]


def assign_codes(records, unique_qids, scope_fn):
    """
    Assign a stable `code` to every record.

    A record that carries a globally-unique Wikidata QID uses that QID as its
    code (the most stable, most "natural" identifier a place has). Otherwise
    the code is a slug of the name, disambiguated by a coordinate hash when a
    name repeats within the same scope.

    `records`      : list of dicts (must have `id`, `name`, `latitude`,
                     `longitude`, `wikiDataId`)
    `unique_qids`  : set of QIDs that appear exactly once across the dataset
    `scope_fn`     : record -> hashable scope (e.g. (country_code, state_code))
    """
    tentative: dict = {}
    counts: Counter = Counter()
    for r in records:
        qid = r.get("wikiDataId")
        if qid and qid in unique_qids:
            code = qid
        else:
            code = slugify(r["name"])
        scope = scope_fn(r)
        tentative[r["id"]] = (scope, code)
        counts[(scope, code)] += 1

    result: dict = {}
    used: set = set()
    for r in records:
        scope, code = tentative[r["id"]]
        if counts[(scope, code)] > 1:
            base = slugify(r["name"])
            h = coord_hash(r.get("latitude"), r.get("longitude"))
            code = f"{base}-{h}"
            suffix = 2
            while (scope, code) in used:
                code = f"{base}-{h}-{suffix}"
                suffix += 1
        used.add((scope, code))
        result[r["id"]] = code
    return result


# --------------------------------------------------------------------------- #
# Field transforms
# --------------------------------------------------------------------------- #

def clean(value):
    """Return value, or None when it is a falsy/blank placeholder."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def split_phone(phonecode):
    if not phonecode:
        return []
    return [p.strip() for p in re.split(r"[,/\s]+", str(phonecode)) if p.strip()]


def currency_object(code, name, symbol):
    if not any((code, name, symbol)):
        return None
    return {"code": clean(code), "name": clean(name), "symbol": clean(symbol)}


def drop_keys(d, *keys):
    return {k: v for k, v in d.items() if k not in keys}


# --------------------------------------------------------------------------- #
# Main conversion
# --------------------------------------------------------------------------- #

def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def convert_countries(src_dir):
    rows = load(os.path.join(src_dir, "countries", "countries.json"))
    out = []
    for c in rows:
        out.append({
            "code": c["iso2"],
            "name": c["name"],
            "iso3": clean(c.get("iso3")),
            "numeric_code": clean(c.get("numeric_code")),
            "phone": split_phone(c.get("phonecode")),
            "capital": clean(c.get("capital")),
            "currency": currency_object(c.get("currency"), c.get("currency_name"), c.get("currency_symbol")),
            "tld": clean(c.get("tld")),
            "native": clean(c.get("native")),
            "population": c.get("population"),
            # Upstream never recorded a year for country populations; we make
            # the unknown explicit rather than silently ambiguous.
            "population_year": None,
            "area_sq_km": c.get("area_sq_km"),
            "region": clean(c.get("region")),
            "subregion": clean(c.get("subregion")),
            "nationality": clean(c.get("nationality")),
            "postal_code_format": clean(c.get("postal_code_format")),
            "postal_code_regex": clean(c.get("postal_code_regex")),
            "timezones": c.get("timezones"),
            "translations": c.get("translations"),
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "emoji": clean(c.get("emoji")),
            "emojiU": clean(c.get("emojiU")),
            "wikiDataId": clean(c.get("wikiDataId")),
        })
    return out


def convert_states(src_dir):
    rows = load(os.path.join(src_dir, "states", "states.json"))
    id_to_code = {s["id"]: s["iso2"] for s in rows}
    out = []
    for s in rows:
        parent = clean(s.get("parent_id"))
        out.append({
            "country_code": s["country_code"],
            "code": s["iso2"],
            "name": s["name"],
            "type": clean(s.get("type")),
            "type_local": clean(s.get("type_local")),
            "level": s.get("level"),
            "parent_code": id_to_code.get(parent) if parent else None,
            "iso3166_2": clean(s.get("iso3166_2")),
            "fips_code": clean(s.get("fips_code")),
            "native": clean(s.get("native")),
            "population": s.get("population"),
            "population_year": None,
            "latitude": s.get("latitude"),
            "longitude": s.get("longitude"),
            "timezone": clean(s.get("timezone")),
            "translations": s.get("translations"),
            "wikiDataId": clean(s.get("wikiDataId")),
        })
    return out


def convert_counties(src_dir):
    rows = []
    for name in sorted(os.listdir(os.path.join(src_dir, "counties"))):
        if name.endswith(".json"):
            rows.extend(load(os.path.join(src_dir, "counties", name)))
    qids = Counter(r.get("wikiDataId") for r in rows if r.get("wikiDataId"))
    unique_qids = {q for q, n in qids.items() if n == 1}

    # `code` is unique within the country, so cross-region counties (which
    # have no single state) can still be referenced cleanly.
    scope = lambda r: (r["country_code"],)
    id_to_code = assign_codes(rows, unique_qids, scope)

    out = []
    for r in rows:
        parent = clean(r.get("parent_id"))
        out.append({
            "country_code": r["country_code"],
            "state_code": clean(r.get("state_code")),
            "code": id_to_code[r["id"]],
            "name": r["name"],
            "type": clean(r.get("type")),
            "type_local": clean(r.get("type_local")),
            "level": r.get("level"),
            "parent_code": id_to_code.get(parent) if parent else None,
            "native": clean(r.get("native")),
            "population": r.get("population"),
            "population_year": None,
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "timezone": clean(r.get("timezone")),
            "translations": r.get("translations"),
            "wikiDataId": clean(r.get("wikiDataId")),
            "states": r.get("states"),
        })
    return out


def convert_cities(src_dir):
    rows = []
    for name in sorted(os.listdir(os.path.join(src_dir, "cities"))):
        if name.endswith(".json"):
            rows.extend(load(os.path.join(src_dir, "cities", name)))
    qids = Counter(r.get("wikiDataId") for r in rows if r.get("wikiDataId"))
    unique_qids = {q for q, n in qids.items() if n == 1}

    # `code` is unique within the country.
    scope = lambda r: (r["country_code"],)
    id_to_code = assign_codes(rows, unique_qids, scope)

    out = []
    for r in rows:
        parent = clean(r.get("parent_id"))
        kind, ntype = classify(r.get("type"))
        out.append({
            "country_code": r["country_code"],
            "state_code": clean(r.get("state_code")),
            "code": id_to_code[r["id"]],
            # Resolved below against the counties table.
            "county_code": None,
            "name": r["name"],
            "kind": kind,
            "type": ntype,
            "type_local": clean(r.get("type_local")),
            "level": r.get("level"),
            "parent_code": id_to_code.get(parent) if parent else None,
            "native": clean(r.get("native")),
            "population": r.get("population"),
            "population_year": r.get("population_year"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "timezone": clean(r.get("timezone")),
            "translations": r.get("translations"),
            "wikiDataId": clean(r.get("wikiDataId")),
            # kept transiently for the county-link resolution step
            "_county_id": r.get("county_id"),
        })
    return out, id_to_code


def convert_regions(src_dir):
    rows = load(os.path.join(src_dir, "regions", "regions.json"))
    return [{"name": r["name"], "translations": r.get("translations")} for r in rows]


def convert_postcodes(src_dir, city_id_to_code):
    rows = []
    for name in sorted(os.listdir(os.path.join(src_dir, "postcodes"))):
        if name.endswith(".json"):
            rows.extend(load(os.path.join(src_dir, "postcodes", name)))

    out = []
    seen = set()
    for r in rows:
        city_id = clean(r.get("city_id"))
        rec = {
            "country_code": r["country_code"],
            "state_code": clean(r.get("state_code")),
            "code": r["code"],
            "locality_name": clean(r.get("locality_name")),
            "type": clean(r.get("type")),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "source": clean(r.get("source")),
            "wikiDataId": clean(r.get("wikiDataId")),
            "city_code": city_id_to_code.get(city_id) if city_id else None,
        }
        # Collapse exact duplicates (a handful of upstream double-imports).
        key = (rec["country_code"], rec["state_code"], rec["code"], rec["locality_name"])
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def convert_subregions(src_dir):
    regions = load(os.path.join(src_dir, "regions", "regions.json"))
    id_to_name = {r["id"]: r["name"] for r in regions}
    rows = load(os.path.join(src_dir, "subregions", "subregions.json"))
    return [
        {"name": r["name"], "region": id_to_name.get(r.get("region_id")), "translations": r.get("translations")}
        for r in rows
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="path to upstream contributions/ directory")
    ap.add_argument("dst", help="path to write data/ directory")
    args = ap.parse_args()

    countries = convert_countries(args.src)
    states = convert_states(args.src)
    counties = convert_counties(args.src)
    cities, city_id_to_code = convert_cities(args.src)
    regions = convert_regions(args.src)
    subregions = convert_subregions(args.src)
    postcodes = convert_postcodes(args.src, city_id_to_code)

    # Build old county id -> natural code for the city -> county link.
    counties_src = []
    for name in sorted(os.listdir(os.path.join(args.src, "counties"))):
        if name.endswith(".json"):
            counties_src.extend(load(os.path.join(args.src, "counties", name)))
    county_qids = Counter(r.get("wikiDataId") for r in counties_src if r.get("wikiDataId"))
    county_unique_qids = {q for q, n in county_qids.items() if n == 1}
    county_scope = lambda r: (r["country_code"],)
    county_id_to_code = assign_codes(counties_src, county_unique_qids, county_scope)

    for c in cities:
        cid = c.pop("_county_id", None)
        if cid:
            c["county_code"] = county_id_to_code.get(cid)

    # Write output
    os.makedirs(args.dst, exist_ok=True)
    def write(name, obj):
        path = os.path.join(args.dst, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=4)
            fh.write("\n")

    write("regions.json", regions)
    write("subregions.json", subregions)
    write("countries.json", countries)
    write("states.json", states)

    os.makedirs(os.path.join(args.dst, "counties"), exist_ok=True)
    os.makedirs(os.path.join(args.dst, "cities"), exist_ok=True)
    os.makedirs(os.path.join(args.dst, "postcodes"), exist_ok=True)

    # counties / cities grouped by country code, mirroring upstream layout
    from collections import defaultdict
    by_country = defaultdict(list)
    for c in counties:
        by_country[c["country_code"]].append(c)
    for cc, recs in sorted(by_country.items()):
        write(os.path.join("counties", f"{cc}.json"), recs)

    by_country = defaultdict(list)
    for c in cities:
        by_country[c["country_code"]].append(c)
    for cc, recs in sorted(by_country.items()):
        write(os.path.join("cities", f"{cc}.json"), recs)

    by_country = defaultdict(list)
    for p in postcodes:
        by_country[p["country_code"]].append(p)
    for cc, recs in sorted(by_country.items()):
        write(os.path.join("postcodes", f"{cc}.json"), recs)

    print(f"countries: {len(countries)}")
    print(f"states:    {len(states)}")
    print(f"counties:  {len(counties)}")
    print(f"cities:    {len(cities)}")
    print(f"postcodes: {len(postcodes)}")
    print(f"regions:   {len(regions)}")
    print(f"subregions:{len(subregions)}")
    print(f"wrote -> {os.path.abspath(args.dst)}")


if __name__ == "__main__":
    main()

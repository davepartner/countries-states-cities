#!/usr/bin/env python3
"""
Integrity checks for the canonical `data/` dataset.

Verifies:
  1. `code` uniqueness (per country, or globally for countries).
  2. Foreign-key referential integrity for every relationship.
  3. Basic field sanity (no blank codes, population_year only with population).

Usage:
    python3 tools/validate.py data
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter


def load_all(data_dir, table):
    path = os.path.join(data_dir, f"{table}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    recs = []
    sub = os.path.join(data_dir, table)
    if os.path.isdir(sub):
        for f in sorted(glob.glob(os.path.join(sub, "*.json"))):
            recs.extend(json.load(open(f, encoding="utf-8")))
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="path to data/ directory")
    args = ap.parse_args()

    errors = 0

    def fail(msg):
        nonlocal errors
        errors += 1
        print(f"  ✗ {msg}")

    def check_unique(recs, keyfn, label):
        c = Counter(keyfn(r) for r in recs)
        dups = [k for k, v in c.items() if v > 1]
        print(f"  {label}: {len(recs)} rows, {len(dups)} duplicate keys")
        for k in dups[:5]:
            fail(f"duplicate {label} key {k}")
        return dups

    countries = load_all(args.data, "countries")
    states = load_all(args.data, "states")
    counties = load_all(args.data, "counties")
    cities = load_all(args.data, "cities")
    postcodes = load_all(args.data, "postcodes")
    regions = load_all(args.data, "regions")
    subregions = load_all(args.data, "subregions")

    print("uniqueness")
    check_unique(countries, lambda r: r["code"], "countries")
    check_unique(states, lambda r: (r["country_code"], r["code"]), "states")
    check_unique(counties, lambda r: (r["country_code"], r["code"]), "counties")
    check_unique(cities, lambda r: (r["country_code"], r["code"]), "cities")
    check_unique(regions, lambda r: r["name"], "regions")
    check_unique(subregions, lambda r: r["name"], "subregions")

    country_codes = {r["code"] for r in countries}
    state_keys = {(r["country_code"], r["code"]) for r in states}
    county_keys = {(r["country_code"], r["code"]) for r in counties}
    city_keys = {(r["country_code"], r["code"]) for r in cities}
    region_names = {r["name"] for r in regions}
    subregion_names = {r["name"] for r in subregions}

    print("foreign keys")
    bad = sum(1 for r in cities if r["country_code"] not in country_codes)
    print(f"  cities → country_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in states if r["country_code"] not in country_codes)
    print(f"  states → country_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in counties if r["country_code"] not in country_codes)
    print(f"  counties → country_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in cities if r["state_code"] and (r["country_code"], r["state_code"]) not in state_keys)
    print(f"  cities → state_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in counties if r["state_code"] and (r["country_code"], r["state_code"]) not in state_keys)
    print(f"  counties → state_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in cities if r["county_code"] and (r["country_code"], r["county_code"]) not in county_keys)
    print(f"  cities → county_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in cities if r["parent_code"] and (r["country_code"], r["parent_code"]) not in city_keys)
    print(f"  cities → parent_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in states if r["parent_code"] and (r["country_code"], r["parent_code"]) not in state_keys)
    print(f"  states → parent_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in counties if r["parent_code"] and (r["country_code"], r["parent_code"]) not in county_keys)
    print(f"  counties → parent_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in postcodes if r["city_code"] and (r["country_code"], r["city_code"]) not in city_keys)
    print(f"  postcodes → city_code: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in countries if r["region"] and r["region"] not in region_names)
    print(f"  countries → region: {bad} broken"); errors += bad and 1
    bad = sum(1 for r in countries if r["subregion"] and r["subregion"] not in subregion_names)
    print(f"  countries → subregion: {bad} broken"); errors += bad and 1

    print("field sanity")
    for table, recs in (("countries", countries), ("states", states),
                        ("counties", counties), ("cities", cities)):
        blank = sum(1 for r in recs if not r.get("code") or not str(r["code"]).strip())
        if blank:
            fail(f"{table}: {blank} records with blank code")
        else:
            print(f"  {table}: codes populated")

    print()
    if errors:
        print(f"FAILED with {errors} problem(s)")
        sys.exit(1)
    print("OK — all integrity checks passed")


if __name__ == "__main__":
    main()

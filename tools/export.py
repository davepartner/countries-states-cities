#!/usr/bin/env python3
"""
Export the canonical `data/` dataset to every distribution format.

Single runtime, Python 3.10+ standard library only (plus optional `pyarrow`
for the Parquet export). No MySQL, no PHP, no Node.

Usage:
    python3 tools/export.py data/ dist/

Formats written under `dist/`:
    json/        combined + per-collection JSON
    csv/         per-collection CSV (nested fields JSON-encoded)
    sql/         MySQL, PostgreSQL, SQLite, SQL Server (schema + data)
    xml/         per-collection XML
    yml/         per-collection YAML
    geojson/     GeoJSON FeatureCollections (Point features)
    mongodb/     NDJSON for mongoimport
    parquet/     columnar Parquet (requires `pyarrow`)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from collections import OrderedDict

# --------------------------------------------------------------------------- #
# Table definitions: column order and SQL types.
# kind: str | int | float | json | bool
# --------------------------------------------------------------------------- #

TABLES = OrderedDict([
    ("regions", {
        "columns": [("name", "str"), ("translations", "json")],
        "pk": ["name"],
    }),
    ("subregions", {
        "columns": [("name", "str"), ("region", "str"), ("translations", "json")],
        "pk": ["name"],
    }),
    ("countries", {
        "columns": [
            ("code", "str"), ("name", "str"), ("iso3", "str"), ("numeric_code", "str"),
            ("phone", "json"), ("capital", "str"), ("currency", "json"), ("tld", "str"),
            ("native", "str"), ("population", "int"), ("population_year", "int"),
            ("area_sq_km", "float"), ("region", "str"), ("subregion", "str"),
            ("nationality", "str"), ("postal_code_format", "str"),
            ("postal_code_regex", "str"), ("timezones", "json"), ("translations", "json"),
            ("latitude", "float"), ("longitude", "float"), ("emoji", "str"),
            ("emojiU", "str"), ("wikiDataId", "str"),
        ],
        "pk": ["code"],
    }),
    ("states", {
        "columns": [
            ("country_code", "str"), ("code", "str"), ("name", "str"), ("type", "str"),
            ("type_local", "str"), ("level", "int"), ("parent_code", "str"),
            ("iso3166_2", "str"), ("fips_code", "str"), ("native", "str"),
            ("population", "int"), ("population_year", "int"), ("latitude", "float"),
            ("longitude", "float"), ("timezone", "str"), ("translations", "json"),
            ("wikiDataId", "str"),
        ],
        "pk": ["country_code", "code"],
    }),
    ("counties", {
        "columns": [
            ("country_code", "str"), ("state_code", "str"), ("code", "str"), ("name", "str"),
            ("type", "str"), ("type_local", "str"), ("level", "int"), ("parent_code", "str"),
            ("native", "str"), ("population", "int"), ("population_year", "int"),
            ("latitude", "float"), ("longitude", "float"), ("timezone", "str"),
            ("translations", "json"), ("wikiDataId", "str"), ("states", "json"),
        ],
        "pk": ["country_code", "code"],
    }),
    ("cities", {
        "columns": [
            ("country_code", "str"), ("state_code", "str"), ("code", "str"),
            ("county_code", "str"), ("name", "str"), ("kind", "str"), ("type", "str"),
            ("type_local", "str"), ("level", "int"), ("parent_code", "str"),
            ("native", "str"), ("population", "int"), ("population_year", "int"),
            ("latitude", "float"), ("longitude", "float"), ("timezone", "str"),
            ("translations", "json"), ("wikiDataId", "str"),
        ],
        "pk": ["country_code", "code"],
    }),
    ("postcodes", {
        "columns": [
            ("country_code", "str"), ("state_code", "str"), ("code", "str"),
            ("locality_name", "str"), ("type", "str"), ("latitude", "float"),
            ("longitude", "float"), ("source", "str"), ("wikiDataId", "str"),
            ("city_code", "str"),
        ],
        # A postal code is not globally unique; postcodes are a flat reference
        # table and carry no primary key (an index is emitted instead).
        "pk": None,
        "index": ["country_code", "code"],
    }),
])

# Insertion order must respect referential integrity.
LOAD_ORDER = ["regions", "subregions", "countries", "states", "counties", "cities", "postcodes"]


def load_data(data_dir):
    data = {}
    for table in TABLES:
        recs = []
        path = os.path.join(data_dir, f"{table}.json")
        if os.path.exists(path):
            recs = json.load(open(path, encoding="utf-8"))
        else:  # split per-country layout (cities/, counties/)
            sub = os.path.join(data_dir, table)
            if os.path.isdir(sub):
                for f in sorted(os.listdir(sub)):
                    if f.endswith(".json"):
                        recs.extend(json.load(open(os.path.join(sub, f), encoding="utf-8")))
        data[table] = recs
    return data


# --------------------------------------------------------------------------- #
# Tabular flattening: nested structures become JSON strings.
# --------------------------------------------------------------------------- #

def to_scalar(value, kind):
    if value is None:
        return None
    if kind == "json":
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def flatten(record, columns):
    return {c: to_scalar(record.get(c), kind) for c, kind in columns}


# --------------------------------------------------------------------------- #
# Serializers
# --------------------------------------------------------------------------- #

def json_serializer(recs, pretty=False):
    if pretty:
        return json.dumps(recs, ensure_ascii=False, indent=4) + "\n"
    return json.dumps(recs, ensure_ascii=False, separators=(",", ":")) + "\n"


def csv_serializer(recs, columns):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([c for c, _ in columns])
    for r in recs:
        flat = flatten(r, columns)
        writer.writerow(["" if flat[c] is None else flat[c] for c, _ in columns])
    return out.getvalue()


def sql_escape(value):
    if value is None:
        return "NULL"
    s = str(value)
    s = s.replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def sql_literal(value, kind):
    if value is None:
        return "NULL"
    if kind == "int":
        return str(int(value))
    if kind == "float":
        return str(float(value))
    if kind == "bool":
        return "1" if value else "0"
    if kind == "json":
        return sql_escape(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return sql_escape(value)


SQL_TYPE_MAP = {
    "str": "TEXT",
    "int": "BIGINT",
    "float": "DOUBLE PRECISION",
    "json": "TEXT",
    "bool": "BOOLEAN",
}


def sql_ddl(dialect, tables=None):
    """Return per-dialect DDL for the given tables (default: all)."""
    tables = tables or LOAD_ORDER
    stmts = []
    for table in tables:
        spec = TABLES[table]
        cols = []
        for c, kind in spec["columns"]:
            ctype = SQL_TYPE_MAP[kind]
            cols.append(f'  "{c}" {ctype}')
        if spec.get("pk"):
            pk = ", ".join(f'"{c}"' for c in spec["pk"])
            cols.append(f"  PRIMARY KEY ({pk})")
        stmts.append(f'CREATE TABLE "{table}" (\n' + ",\n".join(cols) + "\n);")
        for idx in spec.get("index", []):
            stmts.append(f'CREATE INDEX "idx_{table}_{idx}" ON "{table}" ("{idx}");')
    return "\n\n".join(stmts) + "\n"


def sql_inserts(data, tables=None, batch=500):
    tables = tables or LOAD_ORDER
    out = io.StringIO()
    for table in tables:
        spec = TABLES[table]
        cols = [c for c, _ in spec["columns"]]
        col_list = ", ".join(f'"{c}"' for c in cols)
        recs = data[table]
        for i in range(0, len(recs), batch):
            chunk = recs[i:i + batch]
            rows = []
            for r in chunk:
                vals = ", ".join(sql_literal(r.get(c), kind) for c, kind in spec["columns"])
                rows.append(f"({vals})")
            out.write(f'INSERT INTO "{table}" ({col_list}) VALUES\n  ' + ",\n  ".join(rows) + ";\n")
    return out.getvalue()


def xml_serializer(recs, table):
    out = ['<?xml version="1.0" encoding="UTF-8"?>', f"<{table}>"]
    for r in recs:
        out.append(f"  <record>")
        for k, v in r.items():
            if v is None:
                continue
            if isinstance(v, (dict, list)):
                text = json.dumps(v, ensure_ascii=False)
            else:
                text = str(v)
            text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        .replace('"', "&quot;"))
            out.append(f'    <{k}>{text}</{k}>')
        out.append("  </record>")
    out.append(f"</{table}>")
    return "\n".join(out) + "\n"


def yaml_quote(s):
    # Always double-quote strings; escape backslash and double-quote.
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def yaml_serializer(recs, table, columns):
    out = [f"# {table}", ""]
    for r in recs:
        flat = flatten(r, columns)
        out.append("-")
        for c, _ in columns:
            v = flat[c]
            if v is None:
                out.append(f'  {c}: null')
            elif isinstance(v, str):
                out.append(f"  {c}: {yaml_quote(v)}")
            else:
                out.append(f"  {c}: {v}")
    return "\n".join(out) + "\n"


def geojson_serializer(recs, table):
    features = []
    for r in recs:
        lat, lon = r.get("latitude"), r.get("longitude")
        if lat is None or lon is None:
            continue
        try:
            latf, lonf = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lonf, latf]},
            "properties": {k: v for k, v in r.items() if k not in ("latitude", "longitude")},
        })
    return json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, separators=(",", ":")) + "\n"


def parquet_serializer(recs, columns):
    import pyarrow as pa
    import pyarrow.parquet as pq
    flat = [flatten(r, columns) for r in recs]
    table = pa.Table.from_pylist(flat)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_binary(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(blob)


def emit(data, dst, tables=None, formats=None, sql_dialects=None):
    """
    Write every format for the given `tables` (default: all) to `dst`.

    `tables`       — ordered list of table names to emit.
    `formats`      — subset of {json, csv, sql, xml, yml, geojson, mongodb,
                     parquet}; default: all.
    `sql_dialects` — list of {mysql, postgresql, sqlite, sqlserver}; default all.
    """
    tables = tables or LOAD_ORDER
    formats = formats or {"json", "csv", "sql", "xml", "yml", "geojson", "mongodb", "parquet"}
    sql_dialects = sql_dialects or ("mysql", "postgresql", "sqlite", "sqlserver")

    if "json" in formats:
        write(os.path.join(dst, "json", "world.json"),
              json_serializer([{t: data[t]} for t in tables], pretty=True))
        for table in tables:
            write(os.path.join(dst, "json", f"{table}.json"), json_serializer(data[table]))

    if "csv" in formats:
        for table in tables:
            write(os.path.join(dst, "csv", f"{table}.csv"),
                  csv_serializer(data[table], TABLES[table]["columns"]))

    if "sql" in formats:
        ddl = sql_ddl("ansi", tables)
        inserts = sql_inserts(data, tables)
        for dialect in sql_dialects:
            write(os.path.join(dst, "sql", dialect, "schema.sql"), ddl)
            write(os.path.join(dst, "sql", dialect, "data.sql"), inserts)

    if "xml" in formats:
        for table in tables:
            write(os.path.join(dst, "xml", f"{table}.xml"), xml_serializer(data[table], table))

    if "yml" in formats:
        for table in tables:
            write(os.path.join(dst, "yml", f"{table}.yml"),
                  yaml_serializer(data[table], table, TABLES[table]["columns"]))

    if "geojson" in formats:
        for table in tables:
            if table in ("countries", "states", "counties", "cities"):
                write(os.path.join(dst, "geojson", f"{table}.geojson"),
                      geojson_serializer(data[table], table))

    if "mongodb" in formats:
        for table in tables:
            lines = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                            for r in data[table])
            write(os.path.join(dst, "mongodb", f"{table}.ndjson"), lines)

    if "parquet" in formats:
        try:
            for table in tables:
                blob = parquet_serializer(data[table], TABLES[table]["columns"])
                write_binary(os.path.join(dst, "parquet", f"{table}.parquet"), blob)
            print("parquet: written")
        except ImportError:
            print("parquet: skipped (install `pyarrow` to enable)")

    counts = {t: len(data[t]) for t in tables}
    print("exported:", counts)
    print("wrote ->", os.path.abspath(dst))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="path to data/ directory")
    ap.add_argument("dst", help="path to write dist/ directory")
    args = ap.parse_args()

    data = load_data(args.data)
    emit(data, args.dst)


if __name__ == "__main__":
    main()

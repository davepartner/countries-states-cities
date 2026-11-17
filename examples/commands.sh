#!/usr/bin/env bash
# Ready-to-run subset commands. Replace `OUT` with your destination directory.
# Run from the repository root.

# --- scope ladders -----------------------------------------------------------
python3 tools/subset.py data OUT --scope countries                                   # countries only
python3 tools/subset.py data OUT --scope countries,states                             # + states
python3 tools/subset.py data OUT --scope countries,states,counties                    # + counties
python3 tools/subset.py data OUT --scope countries,states,counties,cities             # + cities
python3 tools/subset.py data OUT --scope all                                          # + postcodes

# --- geography filters --------------------------------------------------------
python3 tools/subset.py data OUT --scope countries --region Africa                    # African countries
python3 tools/subset.py data OUT --scope countries,states --region Europe             # European countries + states
python3 tools/subset.py data OUT --scope countries,states,cities --country NG,GH      # cities in Nigeria + Ghana
python3 tools/subset.py data OUT --scope countries,states,cities --state US:CA,US:NY  # cities in California + New York
python3 tools/subset.py data OUT --scope all --country DE                            # Germany, incl. postcodes

# --- formats ------------------------------------------------------------------
python3 tools/subset.py data OUT --scope countries,states,cities --country US \
    --format sql --sql-dialect postgresql                                            # Postgres SQL
python3 tools/subset.py data OUT --scope countries,states --region Europe --format csv
python3 tools/subset.py data OUT --scope countries --region Africa --format geojson  # map
python3 tools/subset.py data OUT --scope all --country NG --format mongodb           # mongoimport
python3 tools/subset.py data OUT --scope countries,states,cities --country US \
    --format sql --sql-dialect mysql --sql-dialect sqlite                            # multiple dialects at once

# --- whole world, every format -------------------------------------------------
python3 tools/export.py data OUT

# --- validate the canonical data before/after any edit -------------------------
python3 tools/validate.py data

"""Clean the raw HDB resale dataset into an analysis-ready table.

Transformations:
- storey_range ("04 TO 06") -> storey_mid (5.0)
- remaining_lease ("61 years 04 months" / "63 years") -> remaining_lease_years
- flat_age_years = registration year - lease_commence_date
- price_per_sqm = resale_price / floor_area_sqm
- month_idx = months since 2017-01 (for trend features)

Drops (all logged to data/processed/cleaning_log.json):
- exact duplicate rows (no unit identifier exists in the source, so an exact
  duplicate on every published field cannot be distinguished from a repeated
  record; the count and this caveat are documented)
- rows with non-positive price or floor area, or unparseable key fields
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw" / "hdb_resale_2017_onwards.csv"
OUT = BASE / "data" / "processed" / "hdb_resale_clean.csv"
LOG = BASE / "data" / "processed" / "cleaning_log.json"

LEASE_RE = re.compile(r"(?:(\d+)\s*years?)?\s*(?:(\d+)\s*months?)?")


def parse_remaining_lease(text: str) -> float:
    m = LEASE_RE.fullmatch(str(text).strip())
    if not m or (m.group(1) is None and m.group(2) is None):
        return np.nan
    years = int(m.group(1)) if m.group(1) else 0
    months = int(m.group(2)) if m.group(2) else 0
    return years + months / 12.0


def parse_storey_mid(text: str) -> float:
    parts = str(text).split(" TO ")
    if len(parts) != 2:
        return np.nan
    lo, hi = int(parts[0]), int(parts[1])
    return (lo + hi) / 2.0


def main() -> None:
    df = pd.read_csv(RAW, dtype=str)
    log = {"raw_rows": int(len(df))}

    numeric = ["floor_area_sqm", "lease_commence_date", "resale_price"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["storey_mid"] = df["storey_range"].map(parse_storey_mid)
    df["remaining_lease_years"] = df["remaining_lease"].map(parse_remaining_lease)

    df["month_dt"] = pd.to_datetime(df["month"], format="%Y-%m")
    df["year"] = df["month_dt"].dt.year
    df["month_idx"] = (df["year"] - 2017) * 12 + (df["month_dt"].dt.month - 1)
    df["flat_age_years"] = df["year"] - df["lease_commence_date"]
    df["price_per_sqm"] = df["resale_price"] / df["floor_area_sqm"]

    # --- drops -------------------------------------------------------------
    n0 = len(df)
    df = df.drop_duplicates()
    log["dropped_exact_duplicates"] = int(n0 - len(df))

    bad = (
        (df["resale_price"] <= 0)
        | (df["floor_area_sqm"] <= 0)
        | df["storey_mid"].isna()
        | df["remaining_lease_years"].isna()
        | df["resale_price"].isna()
        | df["floor_area_sqm"].isna()
    )
    log["dropped_impossible_or_unparseable"] = int(bad.sum())
    df = df.loc[~bad].copy()

    keep = [
        "month", "year", "month_idx", "town", "flat_type", "block",
        "street_name", "storey_range", "storey_mid", "floor_area_sqm",
        "flat_model", "lease_commence_date", "flat_age_years",
        "remaining_lease", "remaining_lease_years", "resale_price",
        "price_per_sqm",
    ]
    df = df[keep].sort_values(["month", "town", "block"]).reset_index(drop=True)

    log["clean_rows"] = int(len(df))
    log["period"] = f"{df['month'].min()} to {df['month'].max()}"
    log["notes"] = [
        "Exact duplicates dropped: the source publishes no unit number, so "
        "rows identical on every field are treated as repeated records; some "
        "could in principle be distinct flats in the same block sold in the "
        "same month on identical terms.",
        "No rows had non-positive prices or floor areas in this extract.",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    LOG.write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()

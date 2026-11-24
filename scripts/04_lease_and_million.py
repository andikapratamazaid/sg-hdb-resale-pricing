"""Lease-decay analysis and million-dollar flat analysis."""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "data" / "processed" / "hdb_resale_clean.csv"
RES = BASE / "data" / "results"

BANDS = [0, 40, 50, 60, 70, 80, 90, 100]
LABELS = ["<40", "40-49", "50-59", "60-69", "70-79", "80-89", "90+"]


def main() -> None:
    df = pd.read_csv(CLEAN)

    df["lease_band"] = pd.cut(
        df["remaining_lease_years"], bins=BANDS, labels=LABELS, right=False
    )
    lease = (
        df.groupby("lease_band", observed=True)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area_sqm=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    top = lease.loc[lease["lease_band"] == "90+", "median_price_per_sqm"].iloc[0]
    lease["vs_90plus_pct"] = (100 * (lease["median_price_per_sqm"] / top - 1)).round(1)
    lease.to_csv(RES / "lease_decay.csv", index=False)

    df["is_million"] = df["resale_price"] >= 1_000_000
    by_year = (
        df.groupby("year")
        .agg(
            transactions=("resale_price", "size"),
            million_dollar_count=("is_million", "sum"),
        )
        .reset_index()
    )
    by_year["million_dollar_share_pct"] = (
        100 * by_year["million_dollar_count"] / by_year["transactions"]
    ).round(3)
    by_year.to_csv(RES / "million_dollar_by_year.csv", index=False)

    by_town_year = (
        df.groupby(["town", "year"])
        .agg(
            transactions=("resale_price", "size"),
            million_dollar_count=("is_million", "sum"),
        )
        .reset_index()
    )
    by_town_year["million_dollar_share_pct"] = (
        100 * by_town_year["million_dollar_count"] / by_town_year["transactions"]
    ).round(3)
    by_town_year.to_csv(RES / "million_dollar_by_town_year.csv", index=False)

    print(lease.to_string(index=False))
    print(by_year.to_string(index=False))


if __name__ == "__main__":
    main()

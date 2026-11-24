"""Market overview: monthly series, town league table, flat-type mix."""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "data" / "processed" / "hdb_resale_clean.csv"
RES = BASE / "data" / "results"


def main() -> None:
    RES.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLEAN)

    monthly = (
        df.groupby(["month", "year", "month_idx"])
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            mean_price=("resale_price", "mean"),
            median_price_per_sqm=("price_per_sqm", "median"),
        )
        .reset_index()
        .sort_values("month_idx")
    )
    monthly.to_csv(RES / "monthly_series.csv", index=False)

    town = (
        df.groupby("town")
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area_sqm=("floor_area_sqm", "median"),
            million_dollar_count=("resale_price", lambda s: int((s >= 1_000_000).sum())),
        )
        .reset_index()
        .sort_values("median_price_per_sqm", ascending=False)
    )
    town["million_dollar_share_pct"] = (
        100 * town["million_dollar_count"] / town["transactions"]
    ).round(2)
    town.to_csv(RES / "town_table.csv", index=False)

    mix = (
        df.groupby(["year", "flat_type"])
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
        )
        .reset_index()
    )
    totals = df.groupby("year").size().rename("year_total")
    mix = mix.join(totals, on="year")
    mix["share_pct"] = (100 * mix["transactions"] / mix["year_total"]).round(2)
    mix.to_csv(RES / "flat_type_mix.csv", index=False)

    print(f"monthly rows: {len(monthly)}, towns: {len(town)}, mix rows: {len(mix)}")
    print(town.head(3).to_string(index=False))
    print(town.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()

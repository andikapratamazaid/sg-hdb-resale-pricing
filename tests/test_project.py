"""Consistency tests: recompute headline numbers from the cleaned data and
check them against the delivered result tables."""
import json
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "data" / "processed" / "hdb_resale_clean.csv"
RES = BASE / "data" / "results"


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CLEAN)


@pytest.fixture(scope="module")
def summary():
    return json.loads((RES / "summary.json").read_text())


def test_clean_row_count(df):
    log = json.loads((BASE / "data" / "processed" / "cleaning_log.json").read_text())
    assert len(df) == log["clean_rows"] == 245_123
    assert log["raw_rows"] - log["dropped_exact_duplicates"] == len(df)


def test_period_coverage(df):
    assert df["month"].min() == "2017-01"
    assert df["month"].max() == "2026-11"
    assert df["month"].nunique() == 119


def test_no_impossible_values(df):
    key = ["resale_price", "floor_area_sqm", "storey_mid",
           "remaining_lease_years", "price_per_sqm"]
    assert df[key].notna().all().all()
    assert (df["resale_price"] > 0).all()
    assert (df["floor_area_sqm"] > 0).all()
    assert df["remaining_lease_years"].between(0, 99).all()


def test_price_per_sqm_derivation(df):
    sample = df.sample(500, random_state=1)
    recomputed = sample["resale_price"] / sample["floor_area_sqm"]
    assert (abs(recomputed - sample["price_per_sqm"]) < 0.01).all()


def test_split_sizes(df, summary):
    train = (df["month"] < "2025-01").sum()
    test = (df["month"] >= "2025-01").sum()
    assert train == summary["train_rows"] == 196_686
    assert test == summary["test_rows"] == 48_437


def test_monthly_median_recompute(df):
    monthly = pd.read_csv(RES / "monthly_series.csv")
    for month in ["2017-01", "2021-06", "2026-11"]:
        expected = df.loc[df["month"] == month, "resale_price"].median()
        got = monthly.loc[monthly["month"] == month, "median_price"].iloc[0]
        assert got == pytest.approx(expected)
        n = (df["month"] == month).sum()
        assert monthly.loc[monthly["month"] == month,
                           "transactions"].iloc[0] == n


def test_million_dollar_tables(df):
    by_year = pd.read_csv(RES / "million_dollar_by_year.csv")
    total = int((df["resale_price"] >= 1_000_000).sum())
    assert by_year["million_dollar_count"].sum() == total == 5_869
    y2024 = by_year.loc[by_year["year"] == 2024].iloc[0]
    share = 100 * (df.loc[df["year"] == 2024, "resale_price"] >= 1_000_000).mean()
    assert y2024["million_dollar_share_pct"] == pytest.approx(round(share, 3), abs=0.01)
    y2017 = by_year.loc[by_year["year"] == 2017].iloc[0]
    assert y2017["million_dollar_count"] == 46


def test_town_table(df):
    town = pd.read_csv(RES / "town_table.csv")
    assert len(town) == 26
    assert town["transactions"].sum() == len(df)
    assert town.iloc[0]["town"] == "CENTRAL AREA"
    central = df.loc[df["town"] == "CENTRAL AREA", "price_per_sqm"].median()
    assert town.iloc[0]["median_price_per_sqm"] == pytest.approx(central)


def test_lease_decay_totals(df):
    lease = pd.read_csv(RES / "lease_decay.csv")
    assert len(lease) == 7
    assert lease["transactions"].sum() == len(df)


def test_model_metrics_sanity(summary):
    m = summary["metrics"]
    assert 0.8 < m["linear_hedonic"]["r2"] < 1.0
    assert 0.8 < m["gradient_boosting"]["r2"] < 1.0
    assert m["gradient_boosting"]["mape_pct"] < m["linear_hedonic"]["mape_pct"]
    assert m["gradient_boosting"]["mae_sgd"] < m["linear_hedonic"]["mae_sgd"]
    by_type = pd.read_csv(RES / "model_metrics_by_flat_type.csv")
    gb = by_type[by_type["model"] == "gradient_boosting"].set_index("flat_type")
    assert gb.loc["4 ROOM", "test_rows"] == 20_997
    assert gb.loc["4 ROOM", "mape_pct"] < 7.0


def test_value_segments():
    seg = pd.read_csv(RES / "value_segments_2026.csv")
    assert (seg["transactions"] >= 30).all()
    assert seg["median_residual_pct"].is_monotonic_increasing
    assert seg.iloc[0]["median_residual_pct"] < 0
    pred = pd.read_csv(RES / "test_predictions.csv")
    cell = pred[(pred["town"] == "TOA PAYOH") & (pred["flat_type"] == "3 ROOM")]
    row = seg[(seg["town"] == "TOA PAYOH") & (seg["flat_type"] == "3 ROOM")].iloc[0]
    assert row["median_residual_pct"] == pytest.approx(
        cell["residual_pct"].median(), abs=0.01)
    assert row["transactions"] == len(cell)


def test_dashboard_and_charts_exist():
    dash = BASE / "dashboard" / "index.html"
    assert dash.exists() and "simulated" in dash.read_text().lower()
    charts = list((BASE / "charts").glob("*.png"))
    assert len(charts) >= 6
    assert all(c.stat().st_size > 10_000 for c in charts)

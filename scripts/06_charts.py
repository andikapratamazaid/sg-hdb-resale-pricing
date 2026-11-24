"""Generate all charts from the processed data and result tables."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "data" / "processed" / "hdb_resale_clean.csv"
RES = BASE / "data" / "results"
CH = BASE / "charts"

plt.rcParams.update({"figure.dpi": 130, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    CH.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH / name, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def main() -> None:
    monthly = pd.read_csv(RES / "monthly_series.csv", parse_dates=["month"])
    town = pd.read_csv(RES / "town_table.csv")
    lease = pd.read_csv(RES / "lease_decay.csv")
    million = pd.read_csv(RES / "million_dollar_by_year.csv")
    imp = pd.read_csv(RES / "feature_importance.csv")
    pred = pd.read_csv(RES / "test_predictions.csv")

    # 1. Monthly median price + volume (dual axis)
    fig, ax1 = plt.subplots(figsize=(10, 4.2))
    ax1.bar(monthly["month"], monthly["transactions"], width=25,
            color="#c9d6e8", label="Transactions")
    ax1.set_ylabel("Transactions per month")
    ax2 = ax1.twinx()
    ax2.plot(monthly["month"], monthly["median_price"] / 1000, color="#b03a2e",
             lw=1.8, label="Median price")
    ax2.set_ylabel("Median price (S$ thousands)")
    ax2.spines["top"].set_visible(False)
    ax1.set_title("HDB resale market: monthly volume and median price, 2017-2026")
    save(fig, "monthly_price_volume.png")

    # 2. Town median price per sqm (horizontal bar)
    t = town.sort_values("median_price_per_sqm")
    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.barh(t["town"], t["median_price_per_sqm"], color="#2e6da4")
    ax.set_xlabel("Median price per sqm (S$)")
    ax.set_title("Median resale price per sqm by town, 2017-2026")
    save(fig, "town_price_per_sqm.png")

    # 3. Lease decay curve
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.plot(lease["lease_band"], lease["median_price_per_sqm"], marker="o",
            color="#b03a2e", lw=2)
    ax.set_xlabel("Remaining lease (years)")
    ax.set_ylabel("Median price per sqm (S$)")
    ax.set_title("Lease decay: median price per sqm by remaining-lease band\n"
                 "(unadjusted medians; mix of towns and flat types differs by band)")
    save(fig, "lease_decay_curve.png")

    # 4. Predicted vs actual (2026 test slice)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.scatter(pred["resale_price"] / 1000, pred["predicted"] / 1000,
               s=3, alpha=0.25, color="#2e6da4")
    lim = [100, 1900]
    ax.plot(lim, lim, color="#b03a2e", lw=1.2)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Actual price (S$ thousands)")
    ax.set_ylabel("Model prediction (S$ thousands)")
    ax.set_title("Gradient boosting: predicted vs actual, 2026 test transactions")
    save(fig, "predicted_vs_actual.png")

    # 5. Million-dollar share by year
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.bar(million["year"].astype(str), million["million_dollar_share_pct"],
           color="#2e6da4")
    ax.set_ylabel("Share of transactions >= S$1m (%)")
    ax.set_title("Million-dollar flats: share of HDB resale transactions by year\n"
                 "(2026 covers Jan-Nov registrations)")
    save(fig, "million_dollar_share.png")

    # 6. Feature importance
    f = imp.sort_values("importance_mean")
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.barh(f["feature"], f["importance_mean"],
            xerr=f["importance_std"], color="#2e6da4", capsize=3)
    ax.set_xlabel("Permutation importance (drop in R2 when shuffled)")
    ax.set_title("What drives HDB resale prices: gradient boosting feature importance")
    save(fig, "feature_importance.png")


if __name__ == "__main__":
    main()

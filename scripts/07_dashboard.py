"""Generate dashboard/index.html from the result tables.

The dashboard is a static, client-facing summary page. It is generated
output: edit this script, not the HTML.
"""
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RES = BASE / "data" / "results"
OUT = BASE / "dashboard" / "index.html"


def money(v: float) -> str:
    return f"S${v:,.0f}"


def main() -> None:
    s = json.loads((RES / "summary.json").read_text())
    town = pd.read_csv(RES / "town_table.csv")
    million = pd.read_csv(RES / "million_dollar_by_year.csv")
    seg = pd.read_csv(RES / "value_segments_2026.csv")
    metrics = pd.read_csv(RES / "model_metrics.csv")

    top_towns = town.head(5)
    bottom_towns = town.tail(5).iloc[::-1]
    under = seg.head(5)
    over = seg.tail(5).iloc[::-1]
    m24 = million.loc[million["year"] == 2024].iloc[0]
    m17 = million.loc[million["year"] == 2017].iloc[0]
    gb = metrics.loc[metrics["model"] == "gradient_boosting"].iloc[0]

    def rows(df, cols, fmts):
        out = []
        for _, r in df.iterrows():
            cells = "".join(f"<td>{fmts[c](r[c])}</td>" for c in cols)
            out.append(f"<tr>{cells}</tr>")
        return "\n".join(out)

    ident = lambda v: v  # noqa: E731
    pct = lambda v: f"{v:+.1f}%"  # noqa: E731
    psqm = lambda v: f"S${v:,.0f}"  # noqa: E731
    num = lambda v: f"{v:,.0f}"  # noqa: E731

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HDB Resale Price Intelligence - Client Dashboard</title>
<style>
body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 2rem auto;
  max-width: 980px; padding: 0 1rem; color: #1a1a1a; line-height: 1.5; }}
h1 {{ font-size: 1.6rem; }} h2 {{ margin-top: 2rem; font-size: 1.2rem; }}
.kpis {{ display: flex; flex-wrap: wrap; gap: 1rem; }}
.kpi {{ background: #eef3f9; border-radius: 8px; padding: 1rem 1.2rem; flex: 1 1 180px; }}
.kpi b {{ display: block; font-size: 1.35rem; color: #2e6da4; }}
table {{ border-collapse: collapse; width: 100%; margin: 0.6rem 0 1.2rem; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 0.35rem 0.5rem; text-align: left; }}
img {{ max-width: 100%; }}
.note {{ background: #fdf6e3; border-radius: 8px; padding: 0.8rem 1rem; font-size: 0.92rem; }}
</style>
</head>
<body>
<h1>HDB Resale Price Intelligence</h1>
<p>Prepared for a Singapore proptech startup building an HDB home-valuation tool.
Data: {s['total_transactions_clean']:,} HDB resale transactions registered
{s['period']} (data.gov.sg, official records). <i>This dashboard belongs to a
simulated freelance engagement created for portfolio purposes; the client
brief is fictional, the data and results are real.</i></p>

<div class="kpis">
<div class="kpi"><b>{money(s['median_price_2025'])}</b>Median resale price, 2025</div>
<div class="kpi"><b>{gb['mape_pct']:.1f}% MAPE</b>Valuation model error (test 2025-2026, R2 {gb['r2']:.2f})</div>
<div class="kpi"><b>{m24['million_dollar_share_pct']:.1f}%</b>Million-dollar share of sales, 2024 (vs {m17['million_dollar_share_pct']:.2f}% in 2017)</div>
<div class="kpi"><b>+{s['lease_effect_pct_per_year_linear']:.1f}%</b>Price effect per extra year of remaining lease</div>
</div>

<h2>Market trend</h2>
<img src="../charts/monthly_price_volume.png" alt="Monthly volume and median price">
<img src="../charts/million_dollar_share.png" alt="Million-dollar share by year">

<h2>Most expensive towns (median price per sqm)</h2>
<table><tr><th>Town</th><th>Transactions</th><th>Median price</th><th>Median S$/sqm</th></tr>
{rows(top_towns, ["town", "transactions", "median_price", "median_price_per_sqm"], {"town": ident, "transactions": num, "median_price": money, "median_price_per_sqm": psqm})}
</table>
<h2>Most affordable towns (median price per sqm)</h2>
<table><tr><th>Town</th><th>Transactions</th><th>Median price</th><th>Median S$/sqm</th></tr>
{rows(bottom_towns, ["town", "transactions", "median_price", "median_price_per_sqm"], {"town": ident, "transactions": num, "median_price": money, "median_price_per_sqm": psqm})}
</table>
<img src="../charts/town_price_per_sqm.png" alt="Town price per sqm">

<h2>Lease decay</h2>
<img src="../charts/lease_decay_curve.png" alt="Lease decay curve">
<p>Holding other factors constant in the hedonic model, each additional year of
remaining lease is associated with about +{s['lease_effect_pct_per_year_linear']:.1f}%
on price. The raw curve above is flatter because older-lease bands mix smaller
flats in central towns with larger flats elsewhere.</p>

<h2>Valuation model</h2>
<img src="../charts/feature_importance.png" alt="Feature importance">
<img src="../charts/predicted_vs_actual.png" alt="Predicted vs actual">
<p>Floor area is the dominant price driver, followed by town and remaining
lease. The gradient boosting model prices a typical resale flat within about
{gb['mape_pct']:.0f}% of its transacted price on unseen 2025-2026 data.</p>

<h2>Segments priced below the model, 2026 (model-relative, not investment advice)</h2>
<table><tr><th>Town</th><th>Flat type</th><th>Transactions</th><th>Median gap vs model</th></tr>
{rows(under, ["town", "flat_type", "transactions", "median_residual_pct"], {"town": ident, "flat_type": ident, "transactions": num, "median_residual_pct": pct})}
</table>
<h2>Segments priced above the model, 2026</h2>
<table><tr><th>Town</th><th>Flat type</th><th>Transactions</th><th>Median gap vs model</th></tr>
{rows(over, ["town", "flat_type", "transactions", "median_residual_pct"], {"town": ident, "flat_type": ident, "transactions": num, "median_residual_pct": pct})}
</table>

<p class="note">Limitations: prices are nominal (not inflation-adjusted). HDB
excludes transactions that may not reflect full market price, such as sales
between relatives. Location is known at block level only; renovation, view,
floor-level amenities and exact distance to MRT are not in the data and are
part of the model's remaining error. "Below the model" means below what flats
with the same recorded attributes transacted at; it is not investment advice.</p>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT} ({len(html):,} chars)")


if __name__ == "__main__":
    main()

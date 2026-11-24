"""Hedonic price model: linear baseline vs gradient boosting.

Target: log(resale_price). Time-based split: train on registrations up to
2024-12, test on 2025-01 onwards (mirrors how a valuation engine would be
deployed: fit on history, predict the future).

Outputs:
- data/results/model_metrics.csv          (overall, both models)
- data/results/model_metrics_by_flat_type.csv
- data/results/feature_importance.csv      (permutation importance, boosting)
- data/results/linear_coefficients.csv     (incl. model-based lease effect)
- data/results/value_segments_2026.csv     (town x flat_type residuals, 2026)
- data/results/test_predictions.csv        (2026 slice: actual vs predicted)
- data/results/summary.json                (headline numbers for README/tests)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE = Path(__file__).resolve().parents[1]
CLEAN = BASE / "data" / "processed" / "hdb_resale_clean.csv"
RES = BASE / "data" / "results"

NUMERIC = [
    "floor_area_sqm", "storey_mid", "remaining_lease_years",
    "flat_age_years", "month_idx",
]
CATEGORICAL = ["town", "flat_type", "flat_model"]
FEATURES = NUMERIC + CATEGORICAL
SPLIT = "2025-01"


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae_sgd": float(mean_absolute_error(y_true, y_pred)),
        "mape_pct": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
        "r2": float(r2_score(y_true, y_pred)),
    }


def main() -> None:
    df = pd.read_csv(CLEAN)
    train = df[df["month"] < SPLIT].copy()
    test = df[df["month"] >= SPLIT].copy()
    print(f"train: {len(train):,} (<=2024-12), test: {len(test):,} (>=2025-01)")

    Xtr, ytr = train[FEATURES], np.log(train["resale_price"])
    Xte, yte = test[FEATURES], np.log(test["resale_price"])

    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
        remainder="passthrough",
    )
    linear = Pipeline([("pre", pre), ("reg", LinearRegression())])
    linear.fit(Xtr, ytr)

    boosting = Pipeline([
        ("pre", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore",
                                   sparse_output=False), CATEGORICAL)],
            remainder="passthrough")),
        ("reg", HistGradientBoostingRegressor(
            max_iter=500, learning_rate=0.06, max_leaf_nodes=63,
            min_samples_leaf=40, random_state=42)),
    ])
    boosting.fit(Xtr, ytr)

    models = {"linear_hedonic": linear, "gradient_boosting": boosting}
    overall, by_type = [], []
    preds = {}
    for name, model in models.items():
        pred_price = np.exp(model.predict(Xte))
        preds[name] = pred_price
        overall.append({"model": name, "test_rows": len(test),
                        **metrics(test["resale_price"].to_numpy(), pred_price)})
        tmp = test[["flat_type"]].copy()
        tmp["actual"] = test["resale_price"].to_numpy()
        tmp["pred"] = pred_price
        for ftype, g in tmp.groupby("flat_type"):
            by_type.append({"model": name, "flat_type": ftype,
                            "test_rows": len(g),
                            **metrics(g["actual"].to_numpy(), g["pred"].to_numpy())})
    pd.DataFrame(overall).to_csv(RES / "model_metrics.csv", index=False)
    pd.DataFrame(by_type).to_csv(RES / "model_metrics_by_flat_type.csv", index=False)
    print(pd.DataFrame(overall).to_string(index=False))

    # Permutation importance for the boosting model (sampled test rows)
    sample = test.sample(n=min(8000, len(test)), random_state=42)
    perm = permutation_importance(
        boosting, sample[FEATURES], np.log(sample["resale_price"]),
        n_repeats=5, random_state=42, n_jobs=-1,
    )
    imp = (
        pd.DataFrame({"feature": FEATURES,
                      "importance_mean": perm.importances_mean,
                      "importance_std": perm.importances_std})
        .sort_values("importance_mean", ascending=False)
    )
    imp.to_csv(RES / "feature_importance.csv", index=False)
    print(imp.to_string(index=False))

    # Linear coefficients -> interpretable effects (incl. lease effect)
    ohe = linear.named_steps["pre"].named_transformers_["cat"]
    cat_names = list(ohe.get_feature_names_out(CATEGORICAL))
    coef = pd.DataFrame(
        {"feature": cat_names + NUMERIC,
         "coef_log_price": linear.named_steps["reg"].coef_}
    )
    coef["pct_effect"] = (np.exp(coef["coef_log_price"]) - 1) * 100
    coef.to_csv(RES / "linear_coefficients.csv", index=False)
    lease_row = coef.loc[coef["feature"] == "remaining_lease_years"].iloc[0]
    area_row = coef.loc[coef["feature"] == "floor_area_sqm"].iloc[0]
    print(f"lease effect per extra year: {lease_row['pct_effect']:.2f}%")
    print(f"floor area effect per sqm: {area_row['pct_effect']:.2f}%")

    # Value segments: 2026 transactions, boosting residuals by town x flat_type
    test26 = test[test["year"] == 2026].copy()
    idx26 = test.index[test["year"] == 2026]
    pos = [test.index.get_loc(i) for i in idx26]
    test26["predicted"] = preds["gradient_boosting"][pos]
    test26["residual_pct"] = (
        100 * (test26["resale_price"] - test26["predicted"]) / test26["predicted"]
    )
    test26[["month", "town", "flat_type", "resale_price", "predicted",
            "residual_pct"]].to_csv(RES / "test_predictions.csv", index=False)

    seg = (
        test26.groupby(["town", "flat_type"])
        .agg(transactions=("resale_price", "size"),
             median_residual_pct=("residual_pct", "median"),
             median_actual=("resale_price", "median"),
             median_predicted=("predicted", "median"))
        .reset_index()
    )
    seg = seg[seg["transactions"] >= 30].sort_values("median_residual_pct")
    seg.to_csv(RES / "value_segments_2026.csv", index=False)
    print("Most below model prediction:")
    print(seg.head(5).to_string(index=False))
    print("Most above model prediction:")
    print(seg.tail(5).to_string(index=False))

    med = df.groupby("year")["resale_price"].median()
    summary = {
        "total_transactions_clean": int(len(df)),
        "period": f"{df['month'].min()} to {df['month'].max()}",
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "split": "train <= 2024-12; test >= 2025-01",
        "median_price_2017": float(med.loc[2017]),
        "median_price_2024": float(med.loc[2024]),
        "median_price_2025": float(med.loc[2025]),
        "median_price_2026_partial": float(med.loc[2026]),
        "lease_effect_pct_per_year_linear": round(float(lease_row["pct_effect"]), 3),
        "floor_area_effect_pct_per_sqm_linear": round(float(area_row["pct_effect"]), 3),
        "metrics": {r["model"]: {k: round(v, 3) for k, v in r.items()
                                 if k not in ("model", "test_rows")}
                    for r in overall},
    }
    (RES / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

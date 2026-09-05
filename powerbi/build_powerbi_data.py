"""Build Power BI model-ready tables from the scored test set.

Design note: the cutoff sweep is precomputed here, but LGD and margin are NOT
baked in. The curve stores cumulative good/bad EXPOSURE at each cutoff, so DAX
can compute profit against What-If parameters:

    Profit = [Cum Good Exposure] * MarginParam - [Cum Bad Exposure] * LGDParam

That keeps the LGD and margin sliders live in Power BI, exactly as the Streamlit
app does, without regenerating any data.

    python build_powerbi_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
SRC = ROOT / "data" / "processed" / "scored_test.csv"
OUT = Path(__file__).parent
STEP = 1           # full resolution; 6k rows is trivial for Power BI


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(SRC).sort_values("p", ignore_index=True)
    n, total_bads = len(d), int(d.y.sum())

    # ------------------------------------------------------------ Fact_Accounts
    acct = d.copy()
    acct["decile"] = pd.qcut(acct.p, 10, labels=False, duplicates="drop") + 1
    acct["risk_band"] = pd.cut(
        acct.p, [0, .05, .10, .20, .30, .50, 1.0],
        labels=["0-5%", "5-10%", "10-20%", "20-30%", "30-50%", "50%+"])
    acct["predicted_loss"] = acct.p * acct.exposure
    acct.to_csv(OUT / "Fact_Accounts.csv", index=False)

    # --------------------------------------------------------- Fact_PolicyCurve
    cum_bad_exp = np.concatenate([[0.0], np.cumsum(d.exposure * d.y)])
    cum_good_exp = np.concatenate([[0.0], np.cumsum(d.exposure * (1 - d.y))])
    cum_bads = np.concatenate([[0], np.cumsum(d.y)])
    P = d.p.values

    ks = np.arange(0, n + 1, STEP)
    rows = []
    for k in ks:
        if k == 0:
            continue
        rows.append({
            "cutoff": round(float(P[min(k, n - 1)]), 4),
            "approved": int(k),
            "approval_rate": round(k / n, 4),
            "bad_rate": round(float(cum_bads[k] / k), 4),
            "capture_rate": round(float(1 - cum_bads[k] / total_bads), 4),
            "cum_good_exposure": round(float(cum_good_exp[k]), 0),
            "cum_bad_exposure": round(float(cum_bad_exp[k]), 0),
        })
    pd.DataFrame(rows).to_csv(OUT / "Fact_PolicyCurve.csv", index=False)

    # ------------------------------------------------------------- Fact_Deciles
    dec = acct.groupby("decile").agg(
        accounts=("y", "size"),
        bad_rate=("y", "mean"),
        mean_predicted=("p", "mean"),
        mean_exposure=("exposure", "mean"),
        total_exposure=("exposure", "sum"),
    ).reset_index().round(4)
    dec.to_csv(OUT / "Fact_Deciles.csv", index=False)

    # ------------------------------------------------------ Fact_ModelBenchmark
    # From the notebook's held-out evaluation.
    pd.DataFrame([
        {"Model": "XGBoost (no SMOTE)", "ROC_AUC": .7808, "Gini": .5616, "PR_AUC": .5664,
         "Brier": .1345, "F1": .545, "Recall": .588, "Mean_Predicted": .2208, "Shipped": True},
        {"Model": "XGBoost + SMOTE", "ROC_AUC": .7771, "Gini": .5543, "PR_AUC": .5580,
         "Brier": .1368, "F1": .537, "Recall": .579, "Mean_Predicted": .2470, "Shipped": False},
        {"Model": "LightGBM", "ROC_AUC": .7766, "Gini": .5531, "PR_AUC": .5576,
         "Brier": .1364, "F1": .533, "Recall": .548, "Mean_Predicted": .2470, "Shipped": False},
        {"Model": "Random Forest", "ROC_AUC": .7741, "Gini": .5482, "PR_AUC": .5484,
         "Brier": .1424, "F1": .532, "Recall": .565, "Mean_Predicted": .2931, "Shipped": False},
        {"Model": "Neural Network (Keras MLP)", "ROC_AUC": .7588, "Gini": .5177, "PR_AUC": .5228,
         "Brier": .1679, "F1": .528, "Recall": .520, "Mean_Predicted": .3846, "Shipped": False},
        {"Model": "Logistic Regression", "ROC_AUC": .7578, "Gini": .5156, "PR_AUC": .5110,
         "Brier": .1914, "F1": .518, "Recall": .551, "Mean_Predicted": .4359, "Shipped": False},
    ]).assign(Actual_Rate=.2213).to_csv(OUT / "Fact_ModelBenchmark.csv", index=False)

    # ----------------------------------------------------- Fact_PolicyComparison
    pd.DataFrame([
        {"Policy": "Approve everyone", "ApprovalRate": 1.000, "BadRate": .221,
         "DefaultsCaptured": .00, "NetProfit_NTD": -6_940_000},
        {"Policy": "Rule: decline 1+ month late", "ApprovalRate": .777, "BadRate": .142,
         "DefaultsCaptured": .50, "NetProfit_NTD": 14_360_000},
        {"Policy": "Model at rule's approval rate", "ApprovalRate": .777, "BadRate": .132,
         "DefaultsCaptured": .54, "NetProfit_NTD": 15_060_000},
        {"Policy": "Model at profit optimum", "ApprovalRate": .591, "BadRate": .105,
         "DefaultsCaptured": .72, "NetProfit_NTD": 17_340_000},
    ]).to_csv(OUT / "Fact_PolicyComparison.csv", index=False)

    print(f"written to {OUT}\n")
    for f in sorted(OUT.glob("*.csv")):
        print(f"  {f.name:<28} {len(pd.read_csv(f)):>5} rows")
    print(f"\n  accounts {n:,} | default rate {d.y.mean():.4f} | "
          f"exposure NT${d.exposure.sum()/1e6:,.1f}M")


if __name__ == "__main__":
    main()

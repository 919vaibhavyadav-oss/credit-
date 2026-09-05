# Credit Policy Dashboard — Power BI build guide

The Streamlit app already does this interactively. This is the Power BI version,
because 23% of analyst job descriptions name Power BI or Tableau specifically
and none of them name Streamlit.

About 35 minutes end to end.

---

## Files here

| File | Rows | What it is |
|---|---|---|
| `Fact_PolicyCurve.csv` | 5,993 | Every possible cutoff, with cumulative good/bad exposure |
| `Fact_Accounts.csv` | 5,993 | Scored accounts + decile + risk band |
| `Fact_Deciles.csv` | 10 | Default rate and exposure per risk decile |
| `Fact_ModelBenchmark.csv` | 6 | Six model families with AUC / Gini / Brier / calibration |
| `Fact_PolicyComparison.csv` | 4 | Approve-all vs rule vs model, at matched and optimal points |
| `DAX_measures.txt` | — | Every measure, ready to paste |

**The design decision worth knowing:** LGD and margin are *not* baked into the
data. The curve stores cumulative exposure, and DAX computes profit against two
What-If parameters. So the sliders stay live, exactly like the Streamlit app,
and nothing needs regenerating when an assumption changes.

---

## Step 1 — Load and model (5 min)

1. **Get data → Text/CSV**, load all five CSVs
2. **Modeling → New parameter → Numeric range**, twice:
   - `LGD` — min 0.45, max 0.95, increment 0.01, default 0.75
   - `Margin` — min 0.06, max 0.33, increment 0.01, default 0.18
3. **Model view** → relate `Fact_Accounts[decile]` to `Fact_Deciles[decile]`

The other tables stay unrelated — they're different grains and joining them
would produce nonsense totals.

## Step 2 — Measures (10 min)

`_Measures` table via **Enter data**, then paste from `DAX_measures.txt`.
Format `Net Profit`, `Revenue`, `Credit Loss` and `Total Exposure` as whole
numbers with a thousands separator; rates as percentage.

---

## Page 1 — Policy

**Slicers, top:** `LGD` and `Margin`. These drive everything below.

**Cards:** `Optimal Cutoff` · `Optimal Approval Rate` · `Optimal Bad Rate` ·
`Optimal Profit` · `Break-even Cutoff`

**Line chart** — X: `approval_rate`, Y: `Revenue`, `Credit Loss`, `Net Profit`
Title: *"Profit is revenue minus loss, and the two cross"*
Add a constant line at Y = 0 from the Analytics pane.

**Line chart** — X: `approval_rate`, Y: `bad_rate`
Title: *"Approve more, and the book gets worse"*
Filter to `approved >= 300` — below that the observed bad rate swings several
points per account and the left tail is visual noise.

**Table** — `Fact_PolicyComparison`, all columns, with a `Model Lift vs Rule`
card beside it.

> The honest framing for this page: the model beats *approve everyone* by a
> mile, but that's a comparison against having no credit function. The number
> to quote is **NT$700k at a matched 77.7% approval rate** against the rule a
> bank would actually run — decline anyone already a month late.

---

## Page 2 — Risk segmentation

**Column chart** — X: `Fact_Deciles[decile]`, Y: `Decile Bad Rate`
Add a constant line at 0.2213 labelled "portfolio average".
Title: *"Bad rates are monotone across all ten deciles"*

**Column chart** — X: `Fact_Deciles[decile]`, Y: `Decile Mean Exposure`
Title: *"Exposure is U-shaped — the biggest balances sit at both ends"*

**Card:** `Top 3 Decile Capture` → *"Share of defaults in the riskiest 30%"*

**Text box** — this is the analytical point of the whole dashboard:

> The safest decile is full of transactors who put real money through the card
> and clear it monthly. The middle deciles are small. The riskiest decile swings
> back near the top — maxed-out revolvers carrying a balance they can't clear.
> Declining a mid-risk account avoids a small loss; declining a top-decile
> account avoids a large one. A policy tuned on account counts alone would
> under-price exactly the segment doing the damage, which is why the
> profit-maximising cutoff sits below the per-account break-even.

---

## Page 3 — Model benchmark

**Bar chart** — Y: `Model`, X: `ROC_AUC`, sorted descending
Conditional-format the bar for `Shipped = True`.
Title: *"Five model families span 0.023 AUC"*

**Scatter** — X: `Mean_Predicted`, Y: `ROC_AUC`, size `Brier`, legend `Model`
Add a constant vertical line at X = 0.2213 (the actual default rate).
Title: *"ROC-AUC does not see calibration"*

This is the strongest visual you'll build. Every SMOTE variant sits to the
right of that line — Logistic Regression at 1.97x the true rate — while their
AUC barely moves. It makes the point in one picture that a review looking only
at AUC would miss the defect entirely.

**Table** — `Fact_ModelBenchmark`, all columns.

---

## Step 3 — Finish

- **View → Themes**, pick one and stay in it
- Real titles on every visual — a sentence, not a field name
- **Save as** `Credit_Policy_Dashboard.pbix` in this folder
- **File → Export → Export to PDF** for a screenshot

---

## Numbers to check once it's built

At the default LGD 75% / margin 18%:

| Measure | Expected |
|---|---|
| Accounts | 5,993 |
| Actual default rate | 22.13% |
| Total exposure | NT$307.7M |
| Calibration gap | −0.05pp |
| Optimal approval rate | ~59% |
| Optimal profit | ~NT$17.3M |
| Break-even cutoff | 0.1935 |
| Model lift vs rule | NT$700k |
| Top-3-decile capture | ~63% |

All reproduce the notebook and README exactly.

---

## What it unlocks

The third CV bullet can then carry both tools:

> **Delivered** a **Power BI dashboard** with **SHAP/LIME** explainability and
> **10-decile risk bands** capturing **63% of defaults** in the top **30%**

Swap "Streamlit" for "Power BI" there, and keep Streamlit in your skills line —
you have both, and Power BI is the one the JDs ask for.

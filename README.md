# Credit Card Default Prediction

Predicting which credit card accounts default next month — and then doing the part
most versions of this project skip: **converting that probability into an actual
credit policy, and pricing what every possible cutoff costs.**

**Data:** [UCI Default of Credit Card Clients #350](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) — 30,000 Taiwanese cardholders, April–September 2005, default measured in October. Event rate 22.12%.

---

## Results

Held-out test set: 5,993 accounts, never seen during training or tuning.

| Model | ROC-AUC | Gini | PR-AUC | Brier | F1\* | Recall\* |
|---|---|---|---|---|---|---|
| **XGBoost (no SMOTE)** | **0.7808** | 0.5616 | **0.5664** | **0.1345** | 0.545 | 0.588 |
| XGBoost + SMOTE | 0.7771 | 0.5543 | 0.5580 | 0.1368 | 0.537 | 0.579 |
| LightGBM | 0.7766 | 0.5531 | 0.5576 | 0.1364 | 0.533 | 0.548 |
| Random Forest | 0.7741 | 0.5482 | 0.5484 | 0.1424 | 0.532 | 0.565 |
| Neural Network (Keras MLP) | 0.7588 | 0.5177 | 0.5228 | 0.1679 | 0.528 | 0.520 |
| Logistic Regression | 0.7578 | 0.5156 | 0.5110 | 0.1914 | 0.518 | 0.551 |

\* at each model's F1-optimal threshold, not at 0.5.

**KS = 0.4313**, peaking at the third risk decile — the riskiest 30% of accounts
hold 63.1% of all defaults against 20.6% of non-defaults. Bad rates are monotone
across all ten deciles, which matters more than the headline figure: a band table
that inverts anywhere can't be used for tiered pricing.

### Policy outcome

At LGD 75% and an 18% net margin on carried balance:

| Policy | Approval rate | Bad rate | Defaults captured | Net profit |
|---|---|---|---|---|
| Approve everyone | 100% | 22.1% | 0% | −NT$6.94M |
| Rule: decline anyone 1+ month late | 77.7% | 14.2% | 50% | NT$14.36M |
| **Model, at the rule's approval rate** | 77.7% | **13.2%** | 54% | **NT$15.06M** |
| Model, at its profit optimum | 59.1% | 10.5% | 72% | NT$17.34M |

**Row 3 is the number worth quoting.** Comparing a model against "approve
everyone" flatters any policy at all — it's a comparison against having no credit
function. The fair question is whether the model beats the policy a bank would
actually run without one: *decline anyone already a month late*. That rule is
genuinely decent, because the model itself leans hard on recent repayment status.

Held to the same 77.7% approval rate, the model books a 13.2% bad rate against the
rule's 14.2% and catches 54% of defaults instead of 50% — worth NT$701k on a
6,000-account book, a ~7% relative reduction in bad rate. Row 4 is a larger number
but a weaker claim, since it compares two different operating points.

---

## Four findings

### 1 · There is a ceiling near 0.78 AUC, and every model family reaches it

Five families — logistic regression, random forest, XGBoost, LightGBM and a Keras
MLP — span **0.023 AUC** in total. When architectures that different converge on
the same number, the binding constraint is the data, not the model.

Six months of statement history simply doesn't contain more signal than that.
Moving past it needs bureau data, application data, or the raw transaction stream —
not a better hyperparameter search. Worth stating plainly because it sets the bar
for reading anyone else's results on this dataset: a reported 0.95 means something
leaked, usually SMOTE applied before the train/test split.

The neural network finishing last is the expected result for tabular data with
strong monotone features, not a failed implementation.

### 2 · SMOTE degraded the model

| Model | Mean predicted risk | vs actual 22.1% |
|---|---|---|
| Logistic Regression | 0.4359 | 1.97× |
| Neural Network | 0.3846 | 1.74× |
| Random Forest | 0.2931 | 1.32× |
| XGBoost / LightGBM | ~0.247 | 1.11× |
| XGBoost (no SMOTE) | 0.2208 | **1.00×** |

SMOTE rebalances the training prior to 50/50, so every resampled model scores a
22%-default book as riskier than it is. **The damage isn't uniform — it scales
with how directly a model encodes its training prior.** Logistic regression and
the MLP both carry an explicit intercept or bias term whose fitted value *is* the
base rate, so they inherit the artificial prior almost intact. The heavily
regularised boosters get shrunk toward the observed data at every split and claw
most of it back.

**ROC-AUC registers none of this**, because it reads only the ordering of
predictions. That's exactly why the defect survives a review where AUC is the only
metric on the slide — and why it becomes fatal downstream, where expected loss
multiplies a probability by money. Feed the policy simulator a probability inflated
by 96% and every currency figure is wrong by 96%, in the direction that declines
profitable customers.

The ablation settles it — same algorithm, same hyperparameters, SMOTE the only
difference. **No-SMOTE wins on every metric: AUC, PR-AUC, Brier, F1, precision, and
the recall SMOTE exists to buy.** The un-resampled model predicts a mean risk of
0.2208 against an actual 0.2213.

This isn't a claim that SMOTE never works — it's a claim about *this* imbalance. At
22%, every class has thousands of examples and gradient boosting already handles a
skewed prior through its loss function. SMOTE earns its keep at 1% or 0.1%, where
the minority class is too thin for a tree to isolate. Applied reflexively here it
added ~29,000 interpolated rows and made everything marginally worse.

**The shipped model uses no resampling.** The SMOTE variants stay in the notebook
deliberately — the comparison is the point.

### 3 · Exposure is U-shaped across the risk spectrum

| Risk decile | Mean exposure | Default rate |
|---|---|---|
| D1 (safest) | NT$65.6k | 3.5% |
| D5 | NT$50.2k | 16.9% |
| D8 (trough) | NT$22.9k | 27.7% |
| D10 (riskiest) | NT$59.9k | 70.2% |

The per-account break-even is analytic: approving one more customer is worth it
while `(1−p) × margin > p × LGD`, i.e. `p < MARGIN / (MARGIN + LGD)` = **0.1935**.
Exposure cancels out — but only if every account is the same size.

The simulation lands stricter, at **0.1775**. Replacing every balance with the
portfolio mean moves it to 0.2200, so the entire gap is an exposure-mix effect.

**The largest balances sit at both ends of the risk spectrum, for opposite
reasons.** The safest decile is full of transactors who put real money through the
card and clear it every month. The middle deciles are small. Then the riskiest
decile swings back to near the top: maxed-out revolvers carrying a balance they
can't clear, defaulting at 70%.

Declining a mid-risk account avoids a small loss; declining a top-decile account
avoids a large one. **A policy tuned on account counts alone systematically
under-prices exactly the segment doing the damage.** It's also why the KS-optimal
cutoff and the profit-optimal cutoff are different points — KS counts accounts,
the profit curve weights them by money at risk.

### 4 · The compliant model is the same model

| Variant | Features | ROC-AUC | Δ |
|---|---|---|---|
| Baseline | 45 | 0.7808 | — |
| Drop `EDUCATION` | 42 | 0.7798 | −0.0009 |
| Drop all protected attributes | 39 | 0.7793 | −0.0015 |

`SEX`, `EDUCATION` and `MARRIAGE` are protected characteristics and can't drive a
credit decision under ECOA / Regulation B or comparable RBI fair-practice
expectations. Their presence in an academic dataset doesn't make them usable.

There was a second, independent reason to look at `EDUCATION`. LIME surfaced
`EDUCATION_4 ≤ 0` as a *risk-raising* factor for every customer examined, including
the lowest-risk one — read literally, *not* being in education category 4 makes you
riskier. Checking it: category 4 is the "other" bucket that the undocumented codes
were folded into, and it defaults at **7.05% against a 22% average**. So the model
correctly learned that membership is protective. But there's no credit story in
which "education code not recorded" makes a borrower safe; far more likely those
records come from a different channel or vintage, and the model is reading
**provenance, not behaviour**. That fails a model-risk review and breaks the moment
data collection changes.

Removal had to be *measured* rather than asserted. It costs **0.0015 AUC** — with
Brier unchanged to four decimals and PR-AUC flat. Which is what the EDA predicted:
demographics move the default rate a few points around 22%, while repayment status
spans 13% to 69%. The behavioural features were carrying the signal all along.

Note how the artefact surfaced: invisible in a ranked importance table, where
`EDUCATION_4` is just a low-scoring row. It only appears when you read a signed,
per-customer explanation and something points the wrong way.

---

## Method

```
raw data
   ├─ audit          codebook validation, event rate, data quality
   ├─ clean          duplicates, undocumented category codes      [row-wise]
   ├─ engineer       utilisation, repayment ratios, delinquency   [row-wise]
   │
   ├─ STRATIFIED SPLIT ─────────────────────────────────────────────┐
   │                                                                │
   │   fitted on TRAIN folds only, inside cross-validation:         │
   │      winsorise → Box-Cox → scale → one-hot → SMOTE → model     │
   │                                                                │
   └────────────────────────────────────────────────────────────────┘
                          │
          evaluation │ SHAP + LIME │ policy simulator
```

The split between what happens before and after that line is the whole leakage
defence, and it's structural rather than a matter of remembering.

An operation may run **before** the split only if each row's output depends on that
row alone. Dropping duplicates and remapping category codes qualify. Winsorising,
Box-Cox, standardisation and SMOTE all *learn parameters from the data* —
percentile bounds, lambdas, means, minority neighbourhoods — so they live inside a
scikit-learn/imblearn pipeline refitted on every training fold. Compute a 99th
percentile across all 30,000 rows and that number is partly determined by the test
set; the model's preprocessing has then seen data it's about to be scored on, and
the result comes out optimistic by an unknowable margin.

The processed splits are deliberately **not** stored preprocessed. There's no
fitted scaler on disk to accidentally reuse.

### Details worth calling out

- **`PAY_AMT1` settles `BILL_AMT2`.** The September payment pays the August
  statement — you don't pay a bill the moment it's issued. So the repayment ratio
  is `PAY_AMT{n} / BILL_AMT{n+1}`, running n = 1…5. Pairing same-numbered columns
  compares a payment against a bill it never paid, produces a plausible-looking
  feature, and no metric flags it.
- **Box-Cox with a learned shift.** Box-Cox requires strictly positive input, but
  bills run as low as −339,603 (overpaid accounts) and thousands of months have
  exactly zero payment. Each column is shifted by `1 − min`, learned on train only,
  which keeps the transform genuinely Box-Cox and invertible. Skew on `PAY_AMT2`:
  **31.99 → 0.19**.
- **Tree models skip Box-Cox and scaling entirely.** Gradient boosting splits on
  rank order, so a monotone transform provably cannot change a single split it
  chooses. Running it anyway costs time and buys nothing.
- **Outliers are winsorised, not dropped.** A client with a NT$900k bill is a real
  client you still have to score. Bounds are learned in `fit`, so test rows are
  clipped to the training distribution and never inform it.
- **Negative bills and over-limit balances are kept.** Both are genuine account
  states carrying real signal — an overpaid account and an over-limit one are
  exactly the customers worth modelling.
- **The undocumented `PAY_*` codes are kept as distinct levels.** The codebook
  defines −1 and 1–9, but the data also contains −2 and 0. Their default rates
  (13.2% and 12.8%) show both behave like "current" — −2 is an account with nothing
  owed, 0 is revolving credit paid to the minimum. Merging them discards a real
  distinction the model can price.

---

## Running it

```bash
pip install -r requirements.txt
```

```bash
jupyter notebook "Credit Card Default Prediction (rebuilt).ipynb"
```

Runs top to bottom on a fresh kernel in about 15 minutes, dominated by the
hyperparameter search. All seeds are fixed, so every number above reproduces
exactly. The converted dataset is committed, so a fresh clone needs no downloads.

---

## Limitations

- **No out-of-time validation.** The split is stratified random and the data covers
  one six-month window, so a forward-looking holdout wasn't possible. A production
  model needs one — drift is the failure mode this setup can't detect.
- **One market, one period.** Taiwan, 2005. The method transfers; the numbers don't.
- **The economic assumptions are chosen, not derived.** LGD 75% and margin 18% are
  illustrative, which is why the sensitivity sweep is the deliverable rather than
  any single cutoff — the optimum ranges **0.06 to 0.46** across plausible
  assumption pairs. A cutoff quoted without its assumptions is meaningless.
- **The 59.1% approval optimum is unconstrained.** No real lender declines 41% of
  its book; that ignores growth, servicing scale, and the fact that a card
  relationship is multi-year rather than the single-period bet this arithmetic
  assumes. The usable output is the curve, not its peak.
- **Exposure is proxied** by the most recent bill. Proper EAD modelling applies a
  credit conversion factor to the undrawn commitment, since distressed borrowers
  typically draw down further before defaulting.
- **Model selection used ROC-AUC**, with the threshold tuned on profit afterwards.
  A cost-sensitive objective during training would be more rigorous.

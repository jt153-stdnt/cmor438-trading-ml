# Product contract

## Users and decisions

**Intended users:** rates traders and risk managers on trading desks who need a quick read on U.S. Treasury rate volatility and curve regime.

**Supported decisions:** sizing risk limits and deciding whether to be cautious before the coming month. For example, giving concluding lines like "the model expects 10Y realized vol well above recent levels, so tighten limits."

**Decisions the product must not automate:** placing trades, pricing options,
or setting hedge ratios. The product forecasts *realized* normal volatility;
pricing a swaption requires *implied* volatility, which this product does not
observe. Its outputs are inputs to a human decision, not decisions.

## Dataset suite
One dataset: **daily U.S. Treasury constant-maturity yields** from FRED.

- **Source:** Board of Governors of the Federal Reserve System, H.15
  Selected Interest Rates, retrieved via FRED (Federal Reserve Bank of
  St. Louis). Series: DGS3MO, DGS6MO, DGS1, DGS2, DGS3, DGS5, DGS7, DGS10.
  Retrieved 2026-11-14.
- **License:** U.S. government data, public domain. A real sample could be
  committed as the CI fixture.
- **Observational unit:** one U.S. bond-market trading day. Each row holds
  the eight yields (percent) at that day's close.
- **Sampling process:** not a sample. Every trading day is included. Yields
  are *constant-maturity* values: Treasury estimates a smooth yield curve
  each day from market quotes on recently issued securities, then reads off
  the yield at fixed maturities. Values are therefore model-derived from
  market prices, not individual traded bond yields. Market holidays appear
  as empty rows and are dropped.
- **Time boundary:** raw data runs 1981-09-01 to 2026-11-12. The project
  uses 1985-01-01 onward. 1981–1984 is excluded as an extreme high-rate
  regime (3-month yield above 15%) unlike the rest of the sample.
- **Feature availability:** a day's yields are known only after that day's
  market close. A prediction made on day *t* uses data through day *t*
  only. Trailing-window features (5-, 21-, 63-day realized vol) use past
  days only. The target uses days *t+1 … t+21* and is never a feature.
- **Target / unsupervised question:**
  - Regression: 10-year realized normal vol over the next 21 trading days
    (bp/year).
  - Classification: whether that vol exceeds the training-set 67th
    percentile.
  - Unsupervised: which factors drive daily curve moves (PCA) and which
    curve regimes have occurred (k-means).
- **Known representativeness limits:**
  - **U.S. only.** Results say nothing about other sovereign curves.
  - **Daily closes only.** Intraday volatility (e.g., moves around Fed
    announcements that reverse by the close) is invisible.
  - **Few regimes.** About 40 years contain only a handful of distinct rate
    regimes (disinflation, zero rates 2009–2015 and 2020–2021, the 2022
    hiking cycle). The test period is dominated by one unusual regime.
  - **Zero lower bound.** Near-zero rates compress short-end volatility, so
    relationships learned there may not transfer.
  - **Curve-fitting method changes.** Treasury has revised its curve-
    estimation method over time, which can shift measured yields slightly.
    These changes are not modeled.

## Task-algorithm matrix


| Course family | Project task | Applicable? | Mathematical justification | Evidence |
| --- | --- | --- | --- | --- |
| Linear regression | Regression | Yes | HAR-style linear model on past realized vol is the standard volatility baseline | Notebook 02 |
| Logistic regression | Classification | Yes | Models log-odds of a high-vol month as linear in features; outputs probabilities | Notebook 03 |
| Nearest neighbors | Regression, Classification | Yes | Similar past market states may precede similar volatility | Notebooks 02, 03 |
| Support vector machines | Classification | Yes (classification only) | Max-margin linear separator for the binary label; the course SVM is a classifier, so it is not used for regression | Notebook 03 |
| Decision trees | Regression, Classification | Yes | Captures thresholds such as "vol is high only when the curve is inverted" | Notebooks 02, 03 |
| Ensembles | Regression, Classification | Yes (random forest) | Averaging bootstrapped trees reduces single-tree variance | Notebooks 02, 03 |
| Neural networks | Regression, Classification | Yes | Can learn nonlinear effects, e.g., vol behaving differently near the zero bound | Notebooks 02, 03 |
| Clustering | Unsupervised | Yes (k-means) | Groups days into curve regimes in factor space | Notebook 04 |
| Dimensionality reduction | Unsupervised, feature engineering | Yes (PCA) | Yield changes across maturities are highly correlated; PCA recovers level, slope, curvature | Notebook 04 |

## Evaluation contract

**Partitions (time-ordered, never shuffled):**
- Train: 1985-01-01 to 2012-12-31
- Validation: 2013-01-01 to 2019-12-31
- Final test: 2020-01-01 to latest available date

A 21-trading-day gap is dropped at each boundary, because each target uses
the next 21 days. PCA, feature scaling, and the 67th-percentile threshold are
fit on training data only. 1981–1984 is excluded as an extreme high-rate
regime unlike the rest of the sample.

**Baselines:**
- Regression: persistence (next-month vol = trailing 21-day vol) and HAR.
- Classification: majority class.

**Metrics:**
- Regression: RMSE and MAE in bp/year.
- Classification: balanced accuracy and log loss, plus a cost view in which
  missing a high-vol month costs more than a false alarm.
- Unsupervised: PCA explained variance; k-means stability across random seeds.

**Selection rule:** choose the model with the best validation metric that
beats its baseline. The final test set is opened once, after selection is
frozen.
**Primary metrics (used for selection):** RMSE for regression; log loss
for classification. Others are reported but do not decide selection.

**Uncertainty evidence:** block bootstrap over contiguous 63-day blocks
(rows overlap in their 21-day targets, so row-level resampling would
understate uncertainty). Report 90% intervals for each metric.

**Condition slices:** report metrics separately for low-rate periods
(3M yield < 1%), hiking cycles, and the top decile of volatility, to show
where models fail rather than only on average.

**Failure thresholds:** a candidate that does not beat persistence RMSE
on validation is not promoted. A classifier whose balanced accuracy is
below 0.55 on validation is not promoted.

**Cost view:** a missed high-vol month (false calm) is treated as 3×
as costly as a false alarm.
## System interfaces

- **Data boundary:** `data/local/treasury_yields.csv` (full, ignored by Git);
  `data/fixtures/` (small real sample for CI).
- **Training command:** to be defined (template `scripts/train.py`).
- **Artifact:** versioned model bundle under `artifacts/`.
- **Prediction API:** returns forecast vol, high-vol probability, current
  regime, and model version.
- **User interface:** a single page showing the above with historical context.
- **Logs, metrics, alerts, rollback:** see `OPERATIONS.md`.
- **Deployment environment:** Docker container built from the template's
  `Dockerfile` / `compose.yaml`, serving the API locally.
## Responsible-use boundary

- **Not trading advice.** This is a course project.
- **No guarantee across regimes.** Forecasts may fail in regimes absent from
  training — e.g., the 2020–2022 zero-rate-to-hiking transition.
- **No causal claim.** The product does not claim to explain why volatility
  changes.
- **Human oversight.** A human makes every decision based on its output.
- **What a good demo does not prove:** strong test-period results do not
  prove the model will hold in the next regime shift.
- **Privacy and security:** no personal data; public market data only;
  no credentials stored in the repo.
- **Fairness:** the product makes no decisions about people, so
  group-fairness metrics do not apply.
- **Misuse:** using forecasts to size real positions without implied-vol
  comparison and human judgment is out of scope and unsupported.
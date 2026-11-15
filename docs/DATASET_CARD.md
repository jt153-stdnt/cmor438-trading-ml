# Dataset card

## Identity and provenance

- **Dataset name**: U.S. Treasury constant-maturity yields, daily
- **Source owner**: Board of Governors of the Federal Reserve System (H.15 Selected Interest Rates), distributed through FRED, Federal Reserve Bank of St. Louis
- **Retrieval method and date**: CSV downloaded 2026-11-14 from
  `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS3MO,DGS6MO,DGS1,DGS2,DGS3,DGS5,DGS7,DGS10`
- **License or access agreemen**: U.S. government data, public domain.  No account or API key required.
- **Immutable version, checksum, or query**: the query URL above, plus the
  SHA-256 of the downloaded file: `87a53455bc7635512089d3f73007a42c041c643c29c0f02baf69e751d1e0e006`
  (16,923 rows, 1962-01-02 to 2026-11-12). FRED data updates daily, so a later download will differ; the checksum identifies this exact copy.

## Observation and sampling

- **What does one row represent?** One calendar business day. After
  cleaning, one U.S. bond-market trading day with the closing yield at
  eight fixed maturities.
- **What population or process produced the rows?** Treasury fits a yield curve each
  trading day from market quotes on recently issued securities and reads
  off yields at fixed maturities. Values are model-derived from market
  prices, not individual bond trades.
- **Which units repeat, interact, or depend on one another?** Rows are
  consecutive days of one time series and are strongly autocorrelated.
  The eight maturities on the same day are highly correlated with each
  other. Rows are therefore not independent, and random row splits are
  invalid.
- **Which time, site, batch, subject, or spatial boundaries matter?** All eight series exist from
  1981-09-01; the project uses 1985-01-01 onward. Partitions are by date:
  train 1985–2012, validation 2013–2019, test 2020–latest, with 21 trading
  days dropped at each boundary because targets look 21 days ahead.

## Schema and measurement

| Column | Meaning | Unit | Notes |
| --- | --- | --- | --- |
| `observation_date` | Trading date | YYYY-MM-DD | Identifier; one row per date |
| `DGS3MO` | 3-month yield | percent | Starts 1981-09-01; reached 0.00 |
| `DGS6MO` | 6-month yield | percent | Starts 1981-09-01 |
| `DGS1` | 1-year yield | percent | |
| `DGS2` | 2-year yield | percent | |
| `DGS3` | 3-year yield | percent | |
| `DGS5` | 5-year yield | percent | |
| `DGS7` | 7-year yield | percent | |
| `DGS10` | 10-year yield | percent | Basis for the volatility target |

**Missing-value convention:** market holidays appear as rows with all
eight yields empty (493 such rows from 1981-09-01 on); these are dropped.
One row, 1981-12-09, is missing only DGS3MO and DGS6MO; it falls before
the project's start date and is dropped. No values are filled in.

**Derived quantities:**
- Daily change Δy in basis points: `(y_t − y_{t−1}) × 100`. Basis points,
  not percent or log changes, because short yields reached 0.00 where
  those are undefined. This matches how rate options quote normal
  (Bachelier) volatility.
- **Regression target:** `vol_t = √252 × std(Δy10[t+1 … t+21])`, in
  bp/year.
- **Classification target:** 1 if `vol_t` exceeds the 67th percentile of
  training-set targets, else 0.

**Availability time:** a day's yields are known only after that day's
close. A prediction made on day *t* uses rows up to and including *t*.

**Leakage risks and controls:**
- The target is built from days *t+1 … t+21*. It must never be a feature,
  and targets near a partition boundary overlap the next partition. That
  is why 21 days are dropped at each boundary.
- Trailing features (5-, 21-, 63-day realized vol) must use only days up
  to *t*.
- PCA loadings, feature scaling, and the 67th-percentile threshold are
  fit on training rows only, then applied to validation and test.
- Overlapping 21-day targets make neighboring rows nearly identical, so
  uncertainty estimates must use block resampling, not row-level
  resampling.

## Data access and privacy

- **No personal data.** Market-level public data only.
- **Committed:** a small real sample under `data/fixtures/` for CI, since
  the data is public domain.
- **Local only:** the full file at `data/local/treasury_yields.csv`,
  ignored by Git so the repo stays small.
- **Credentials:** none.
- **CI:** tests run on the committed fixture and never download from FRED,
  so CI works offline and deterministically.

## Representativeness and limitations

- **U.S. only.** Says nothing about other countries' rates.
- **Daily closes only.** Intraday moves that reverse by the close (e.g.,
  around Fed announcements) are invisible.
- **Few regimes.** About 40 years contain a handful of distinct rate
  regimes: disinflation, near-zero rates (2009–2015, 2020–2021), the 2022
  hiking cycle. The test period is dominated by one unusual regime.
- **Zero lower bound.** Short-end volatility is compressed near zero, so
  relationships learned there may not transfer.
- **Measurement changes.** Treasury has revised its curve-fitting method
  over time, which can shift measured yields slightly. Not modeled.
- **Constant-maturity values are interpolated.** They are not prices of
  traded securities, so the dataset is not evidence about any specific
  bond's tradable yield.
- **Not evidence for:** implied volatility, option prices, or the cause
  of volatility changes.
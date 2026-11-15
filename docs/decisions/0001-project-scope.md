# ADR 0001: Project scope

- Status: proposed
- Date: 2026-11-15

## Context

The final project must be one coherent product built on a dataset that
supports a regression task, a classification task, and an unsupervised
task, using lawfully accessible data with a CI-safe fixture committed to a
public repository. The intended user is a rates trader or risk manager who
needs a forward-looking read on U.S. Treasury volatility and curve regime.

Volatility, unlike price direction, is persistent and therefore forecastable,
and it is the unobservable input to option pricing models. Rate options are
priced with the Bachelier (normal) model, whose volatility is quoted in basis
points — the quantity this project forecasts.

## Decision

Build a **Treasury rate-volatility monitor** on daily FRED constant-maturity
yields (3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y), 1985–present:

- **Regression:** 10Y realized normal volatility over the next 21 trading
  days, in bp/year.
- **Classification:** whether that volatility exceeds the training-set 67th
  percentile.
- **Unsupervised:** PCA on daily yield changes (level, slope, curvature) and
  k-means curve regimes.
- **Evaluation:** time-ordered splits (train 1985–2012, validation 2013–2019,
  test 2020–latest) with a 21-trading-day gap at each boundary.

## Alternatives considered

- **S&P 500 implied vs. realized volatility (VIX).** Closest to options and
  Black–Scholes, but S&P 500 index levels require written permission from
  S&P Dow Jones Indices to reproduce, FRED carries only 10 years of daily
  history for them, and VIX data is owned by Cboe. A public CI fixture would
  have to be synthetic. Rejected for licensing risk and shorter history.
- **G10 FX volatility.** Public-domain data and a clean story (Garman–
  Kohlhagen pricing, a PCA "dollar factor"), but cross-currency
  dependencies add complexity without a clearer user. Kept as a possible
  extension.
- **Learning Black–Scholes prices or an implied-volatility surface directly.**
  Historical option-chain data is not freely available, and fitting
  simulated prices conflicts with the course's preference for real
  observational data. Rejected.
- **Predicting yield direction or curve steepening.** Close to a coin flip on
  daily data, so evidence would be weak. Rejected as the primary
  classification target.

## Consequences

- **Benefits:** public-domain data allows a real committed fixture; about
  10,000 usable trading days; PCA on the yield curve is a well-known,
  defensible unsupervised result; every course algorithm family applies.
- **Costs and risks:** overlapping 21-day targets make rows dependent, so
  uncertainty needs block resampling; the 2020–present test period is a
  regime (zero rates, then rapid hikes) unlike most of training, so test
  performance may be poor; daily closes miss intraday volatility.
- **Follow-up work:** data adapter and fixture; target and split code with
  leakage tests; student implementations of each algorithm family.
- **Revisit if:** the professor rejects the topic; validation shows no model
  beats persistence (then reframe the classification target or horizon); or
  the 2020–present test regime makes the product claims indefensible.

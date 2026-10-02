# Implementation notes and reproduction boundaries

These notes compare the supplied code with its original documentation. Important behavior is retained; discrepancies are documented rather than silently repaired.

- The original README describes a 60-day average and 21-trading-day rebalancing. Default code uses a 200-day average together with a 20-day average; intervals are evaluated as calendar-day differences.
- Notebook configurations include both `use_risk_parity=True` and `False`. Several comments disagree with the Boolean values; actual assignments determine the profiles.
- The source file is `risk_parity_strategy.py`, while the old notebook imports an installed `risk_parity_etf_strategy` module. New entry points load the bundled source directly.
- Disabling risk parity or meeting the original exception conditions selects inverse-volatility fallback weights. Market-regime adjustments, exposure scaling, and single-asset caps can subsequently produce a portfolio with unequal risk contributions.
- `ArrayManager(size=300)` determines full initialization, regardless of the shorter covariance or volatility lookback.
- The strategy's `update_trade` callback updates internal cash. Commission settings should match the engine; internal cash does not account for the absolute slippage expense in engine results.
- Nonpositive `total_equity` is replaced by 1.0 in the original implementation. This handling, normalization, and weight-drift logic remain unchanged.
- Overseas ETFs are classified as `overseas`, not automatically scaled using the `equity` market-regime multipliers. The original classification table remains intact.

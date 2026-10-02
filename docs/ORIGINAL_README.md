# Risk Parity Strategy Backtest

## Overview

This strategy implements a **Risk Parity** allocation approach across a multi-asset portfolio, with additional market sentiment adjustments and dynamic risk management.

The backtest is conducted using the **`PortfolioStrategy`** module of **vn.py**.

---

## Portfolio Composition

| Asset Class | Instruments |
|-------------|-------------|
| **Equity (Domestic)** | CSI 300 ETF, CSI 500 ETF, ChiNext ETF |
| **Bonds** | Short-term Treasury ETF, 10-year Treasury ETF |
| **Global Sentiment** | NASDAQ ETF |
| **Safe Haven** | Gold ETF |
| **Commodities** | Non-gold Commodity ETFs |

---

## Strategy Logic

### 1. Core Risk Parity Mechanism

The portfolio is constructed so that **each asset contributes equally to total portfolio risk**.

At each rebalance date:

1. Compute the **covariance matrix** using historical returns of all assets
2. Solve for optimal weights that equalize each asset's **marginal risk contribution**
3. Rebalance the portfolio every **21 trading days** (approximately monthly)

**Mathematical formulation:**

- Portfolio volatility: `σ_p = sqrt(wᵀ Σ w)`
- Marginal risk contribution of asset i: `MRCᵢ = (Σ w)ᵢ / σ_p`
- Risk contribution of asset i: `RCᵢ = wᵢ × MRCᵢ`
- Objective: `RC₁ = RC₂ = ... = RCₙ`

---

### 2. Market Sentiment Adjustment

On each rebalancing day, the strategy adjusts allocations based on the **60-day simple moving average (SMA)** of the CSI 300 Index:

| Signal | Condition | Adjustment |
|--------|-----------|------------|
| **Bull Market** | Price > 60-day SMA | Increase equity ETF weights |
| **Bear Market** | Price ≤ 60-day SMA | Decrease equity ETF weights; increase bond and gold ETF weights |

This dynamic overlay allows the strategy to tilt toward risk-on or risk-off positioning based on prevailing market trends.

---

### 3. Risk Management: Dual Stop-Loss Mechanism

The strategy incorporates two layers of protection:

| Stop-Loss Type | Description |
|----------------|-------------|
| **Dynamic Trailing Stop** | Stop-loss level moves upward as the portfolio gains, locking in profits |
| **Absolute Hard Stop** | Hard threshold that triggers immediate exit regardless of market conditions |

---

## Backtest Framework

- **Platform**: vn.py (`PortfolioStrategy` module)
- **Rebalance Frequency**: Every 21 trading days
- **Universe**: Multi-asset ETFs (see composition above)

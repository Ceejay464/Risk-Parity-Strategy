# Parameter profiles

The primary profile is extracted value for value from the first original notebook backtest. Omitted settings retain the original class defaults. Other notebook profiles are saved separately, without merging or optimization.

| Parameter | Strategy-class default | Primary notebook configuration |
| :--- | ---: | ---: |
| `rebalance_interval` | `21` | `21` |
| `use_dynamic_weights` | `True` | `True` |
| `volatility_lookback` | `60` | `60` |
| `target_portfolio_vol` | `0.08` | `0.15` |
| `use_market_regime` | `True` | `True` |
| `ma_trend_lookback` | `200` | `200` |
| `use_risk_parity` | `True` | `True` |
| `risk_parity_lookback` | `60` | `30` |
| `risk_parity_max_iter` | `100` | `1000` |
| `risk_parity_tolerance` | `1e-06` | `1e-06` |
| `max_position_pct` | `0.95` | `0.7` |
| `min_position_pct` | `0.4` | `0.3` |
| `single_etf_max_pct` | `0.5` | `0.35` |
| `use_full_capital` | `True` | `True` |
| `max_drawdown_stop` | `0.18` | `0.2` |
| `trailing_stop` | `0.1` | `0.12` |
| `stop_loss_days` | `20` | `20` |
| `use_dynamic_stop` | `True` | `False` |
| `peak_multiplier` | `0.5` | `0.6` |
| `rebalance_threshold` | `0.1` | `0.1` |
| `bullish_equity_multiplier` | `1.2` | `1.2` |
| `bullish_bond_multiplier` | `0.8` | `0.8` |
| `bearish_equity_multiplier` | `0.7` | `0.7` |
| `bearish_gold_multiplier` | `1.4` | `1.4` |
| `bearish_bond_multiplier` | `1.1` | `1.1` |
| `price_add` | `0.01` | `0.01` |
| `initial_capital` | `1000000` | `1000000` |
| `commission_rate` | `0.0003` | `0.0003` |

`capital` is the initial backtest ledger balance. Risk parity's `initial_capital` also controls its internal estimated cash ledger; the two should agree. Commission `rate=0.0003`, absolute per-share `slippage=0.001`, contract `size=1`, and `pricetick=0.001` follow the original notebook configuration.

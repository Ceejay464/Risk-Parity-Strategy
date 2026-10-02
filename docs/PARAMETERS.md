# 参数配置

主配置逐值提取自原 Notebook 第一段回测；未填写项继续使用原策略类默认值。原 Notebook 其他配置单独保存，不合并、不优化参数。

| 参数 | 策略类默认值 | Notebook 主配置 |
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

`capital` 是回测账本初始资金；风险平价的 `initial_capital` 同时控制策略内部估算账本，两者应一致。`rate=0.0003`、`slippage=0.001`（每份绝对价格单位）、`size=1`、`pricetick=0.001` 来自原 Notebook。

# Local reproduction

## 1. Environment

Extract the archive and work from the directory containing README.md. Base entry points require Python 3.10+. The verified environment used Python 3.13, NumPy 2.4.4, pandas 3.0.2, and openpyxl 3.1.5.

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` lists base dependency ranges. `requirements-tested.txt` records actual verified versions, without claiming coverage of all Python versions. Optional original-notebook dependencies are listed in `requirements-notebooks.txt`; base entry points need no SciPy, Matplotlib, Plotly, or Jupyter installation.

## 2. Input data

Price input is a CSV/Excel long table: `date,symbol,open,high,low,close`.
Symbols use vn.py notation such as `510300.SSE` and `159915.SZSE`. Each date must contain every configured symbol.
Dates must be daily and timezone-naive. Duplicate rows or invalid OHLC values are rejected, without forward filling.

Configurations contain `symbols,setting,capital,rate,slippage,profile`. Copy an existing JSON file to make a custom profile.
`rate` is commission as a fraction of turnover; `slippage` is an absolute price expense per ETF share.

The lightweight adapter supports only APIs used by the bundled strategy. It registers compatibility modules in a separate Python process
and never edits an installed vn.py package. Limit orders are matched against subsequent OHLC bars, with whole-order fills and pending-order
replacement on rebalancing. There is no partial-fill, broker, margin, dividend, or cash-constraint model.

Original classes still generate all signals and states. Initialization is counted in daily slices; its boundary and calendar behavior have not
been proven equivalent to the native engine. Lightweight and native outputs are labeled separately.

Risk parity requires 300 bars for every asset before full initialization. Provide substantially more than 300 dates; the demonstration contains 640.

## 3. Run

```bash
python -m local.run --demo --output runs/demo
python -m local.run --prices /path/to/prices.csv --config config/notebook_primary.json --output runs/local_csv
```

Use `python -m local.run --help` for all options.

## Native vn.py without a GUI

Use a separate environment to retain the lightweight environment's reproducibility:

```bash
python -m venv .venv-vnpy
# macOS / Linux
source .venv-vnpy/bin/activate
# Windows PowerShell: .venv-vnpy\Scripts\Activate.ps1
python -m pip install -r requirements-vnpy.txt
python -m local.run_vnpy --demo --output runs/native_demo
python -m local.run_vnpy --prices /path/to/prices.csv --output runs/native_real
```

This entry point calls native `BacktestingEngine` and loads the original bundled class.
CSV bars are injected into `history_data[(datetime, vt_symbol)]` and `dts`. It does not invoke database `load_data()`,
start a GUI, or change third-party installation files.

The interface follows the [official engine source](https://github.com/vnpy/vnpy_portfoliostrategy/blob/main/vnpy_portfoliostrategy/backtesting.py).
**A complete native run remains unverified:** the native dependencies were not installed in the verification environment.
Check your installed version if its interface differs; lightweight results do not substitute for native verification.
After installation, save `python -m pip freeze` as your own environment lock file.

## 4. Read outputs

Open your run's `report.html` directly in a browser. Reports use tables and do not generate additional unapproved images.

- `equity.csv`: daily engine equity plus presentation-only `normalized_equity` and `drawdown` fields.
- `trades.csv`: original-engine or adapter transaction records, labeled accordingly.
- `summary.json`: configuration, data kind, dependency versions, and input/source SHA-256 hashes.
- `run.log`: original strategy logs.
- `strategy_states.json` and `pending_orders.json`: lightweight state snapshots and terminal pending orders.
- `native_daily.csv` and `native_statistics.json`: native engine results.

Terminal positions are retained, without an added forced liquidation. Select a fresh output directory for another run.

## 5. Verify retained sources and entry-point boundaries

```bash
python -m local.verify_originals
python -m unittest discover -s tests -v
```

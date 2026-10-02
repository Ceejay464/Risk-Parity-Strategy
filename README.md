# Enhanced Risk Parity ETF Strategy

**Risk contributions · Market-regime adjustment · Volatility targeting · Position limits**

![Risk Parity strategy schematic](assets/teaser.png)

The original vn.py `EnhancedRiskParityStrategy` estimates base weights through covariance-based risk-contribution
iterations. Inverse-volatility weights are used when risk parity is disabled or the original fallback conditions apply.
Market-regime and exposure adjustments then follow the unchanged implementation.

| Component | Actual implementation |
| :--- | :--- |
| Base weights | Risk parity or inverse volatility; lookbacks depend on the selected configuration |
| Market regime | Default 200-day and 20-day averages together with the latest price |
| Volatility targeting | Exposure adjustment; the capital-management modes use different scaling paths |
| Position limits | Total exposure and individual ETF caps; internal cash updated on fills |
| Rebalancing | Calendar-date interval or weight drift; at most once per date |
| Risk controls | Peak drawdown, recent trailing stop, optional threshold tightening, and cooldown |

The notebooks include both enabled and disabled risk-parity profiles. The local entry point defaults to the first profile;
others are stored separately. The original `ArrayManager` holds 300 bars, so adequate initialization history is required.

## Quick start

```bash
python -m pip install -r requirements.txt
python -m local.run --demo --output runs/demo_risk_parity
```

The standalone lightweight adapter loads the original class and uses 640 synthetic business-day slices. This verifies
the execution path, not historical investment performance or equivalence to native vn.py matching.

For user data and the native, headless engine:

```bash
python -m pip install -r requirements-vnpy.txt
python -m local.run_vnpy --prices /path/to/prices.csv --output runs/native_risk_parity
```

The original vn.py database and `close_price.xlsx` are not included. The native entry point loads local CSV data directly
and does not require copying the strategy into a third-party installation's `my_strategies` directory.

## Original research and parameters

- [Original notebook](RiskParityETFStrategy/RiskParityETFStrategy.ipynb)
- [English research document](RiskParityETFStrategy/Risk_Parity_Research_EN.docx)
- [Complete parameter comparison](docs/PARAMETERS.md)
- Original implementation: `RiskParityETFStrategy/risk_parity_strategy.py`

## Explore and reproduce

| File | Purpose |
| :--- | :--- |
| [Quickstart.ipynb](Quickstart.ipynb) | Guided entry point; original research notebooks remain available |
| [PROJECT_OVERVIEW.html](PROJECT_OVERVIEW.html) | Offline project overview, opened directly in a browser |
| [docs/REPRODUCE.md](docs/REPRODUCE.md) | Environment setup, data schema, commands, and outputs |
| [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md) | Actual code behavior, documentation discrepancies, and boundaries |
| [docs/VALIDATION.md](docs/VALIDATION.md) | Completed checks and unverified items |
| [docs/ORIGINAL_README.md](docs/ORIGINAL_README.md) | Archived original README, including previously reported results |
| [CHANGELOG.md](CHANGELOG.md) | Scope of changes |

Each run writes daily equity, trades, parameter and data fingerprints, a log, and a table-only HTML report to `runs/`.
Nonempty output directories are never overwritten. Choose a new `--output` for each run.

## Preserve the strategy

The strategy calculations, parameters, data fields, and identifiers are preserved. Comments, docstrings, and reader-facing logs are translated. Exact original sources are retained in `archive/originals/`.
New entry points live in `local/`: no parameter optimization, additional trading rules, or changes to exercise or rollover logic.
Original notebook calculations and execution counts are retained. Comments, descriptive strings, and displayed output labels are translated; programmatic fields remain intact. English navigation is added at the top.
English research documents and market-data files are retained as source materials.

`docs/original_manifest.json` records original file hashes and retained locations. Run
`python -m local.verify_originals` to verify original archive bytes, unchanged data, and translated executable semantics.

The teaser is a user-approved strategy schematic, not a backtest result. Synthetic fixtures are selected only with an explicit `--demo`.
Previously reported results, synthetic demonstrations, and user-data runs are labeled separately.

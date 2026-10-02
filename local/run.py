"""Run the unchanged original strategy in a separate lightweight replay process."""
from pathlib import Path
import argparse
import json
import numpy as np
from .common import load_panel, select_dates, prepare_output, run_log, export_run
from .daily_adapter import install_compatibility_modules, load_strategy, DailyReplay

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "Risk Parity / Dynamic Allocation"
SOURCE = ROOT / "RiskParityETFStrategy/risk_parity_strategy.py"
CLASS_NAME = "EnhancedRiskParityStrategy"


def read_config(path):
    config = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if set(config) != {"symbols", "setting", "capital", "rate", "slippage", "profile"}:
        raise ValueError("Unexpected configuration keys; use a bundled config as a template")
    if not isinstance(config["setting"], dict) or not config["symbols"]:
        raise ValueError("Configuration needs symbols and a setting object")
    for k in ["capital", "rate", "slippage"]:
        if not np.isfinite(config[k]) or config[k] < 0:
            raise ValueError(f"Invalid {k}")
    if config["capital"] <= 0:
        raise ValueError("capital must be positive")
    return config


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--prices")
    p.add_argument("--config", default=str(ROOT / "config/notebook_primary.json"))
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--output", default="runs/local_demo")
    args = p.parse_args()
    if args.demo and args.prices:
        p.error("--demo cannot be combined with --prices")
    if not args.demo and not args.prices:
        p.error("Provide --prices or explicitly choose --demo")
    try:
        config = read_config(args.config)
        panel, price_path = load_panel(ROOT / "examples/demo_prices.csv" if args.demo else args.prices)
        panel = select_dates(panel, args.start, args.end)
        if set(panel["symbol"].unique()) != set(config["symbols"]):
            raise ValueError("Price symbols must exactly match config symbols")
        install_compatibility_modules()
        cls = load_strategy(SOURCE, CLASS_NAME)
        output = prepare_output(args.output)
        replay = DailyReplay(config["capital"], config["rate"], config["slippage"])
        with run_log(output):
            results, strategy = replay.run(cls, panel, config["setting"])
        (output / "strategy_states.json").write_text(json.dumps(replay.state_history,
            ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        (output / "pending_orders.json").write_text(json.dumps(replay.pending,
            ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        export_run(ROOT, output, results, replay.trades, config["capital"], {
            "project": PROJECT, "accent": "#7855d4", "demo": args.demo,
            "data_kind": "SYNTHETIC DEMO DATA — not historical returns" if args.demo else "User-supplied daily CSV; lightweight replay",
            "engine": "Local DailyReplay adapter (NOT vn.py)",
            "parameters": vars(args), "profile": config,
            "terminal_positions": dict(strategy.pos_data),
            "execution_note": "The original strategy calculations are loaded with English comments and logs. Daily limit orders "
                              "are matched against subsequent OHLC bars. Whole-order fills, "
                              "no cash/margin check, no corporate actions; initializer consumes "
                              "daily slices. This adapter has not been proven equivalent to vn.py. "
                              "Use local.run_vnpy for native results. Slippage is a ledger cost, "
                              "separate from original strategy-internal cash accounting.",
        }, [price_path, args.config])
    except (ValueError, FileNotFoundError) as e:
        p.error(str(e))


if __name__ == "__main__":
    main()

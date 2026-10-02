"""Headless native vn.py entry point, loading local CSV without a database."""
from pathlib import Path
import argparse
import importlib.util
import json
import pandas as pd
from .common import load_panel, select_dates, prepare_output, run_log, export_run
from .run import read_config, ROOT, SOURCE, CLASS_NAME, PROJECT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--prices")
    p.add_argument("--config", default=str(ROOT / "config/notebook_primary.json"))
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--output", default="runs/native_vnpy")
    args = p.parse_args()
    if args.demo and args.prices:
        p.error("--demo cannot be combined with --prices")
    if not args.demo and not args.prices:
        p.error("Provide --prices or explicitly choose --demo")
    try:
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.trader.object import BarData
        from vnpy_portfoliostrategy.backtesting import BacktestingEngine
    except ImportError as e:
        p.error(f"Native vn.py dependencies unavailable: {e}. Install requirements-vnpy.txt "
                "in a separate environment, or use python -m local.run --demo")
    try:
        config = read_config(args.config)
        panel, price_path = load_panel(ROOT / "examples/demo_prices.csv" if args.demo else args.prices)
        panel = select_dates(panel, args.start, args.end)
        if set(panel["symbol"].unique()) != set(config["symbols"]):
            raise ValueError("Price symbols must exactly match config symbols")
        spec = importlib.util.spec_from_file_location("original_native_strategy", SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, CLASS_NAME)
        symbols = config["symbols"]
        engine = BacktestingEngine()
        engine.set_parameters(vt_symbols=symbols, interval=Interval.DAILY,
            start=panel["date"].min().to_pydatetime(), end=panel["date"].max().to_pydatetime(),
            rates={s: config["rate"] for s in symbols},
            slippages={s: config["slippage"] for s in symbols},
            sizes={s: 1 for s in symbols}, priceticks={s: 0.001 for s in symbols},
            capital=config["capital"])
        engine.add_strategy(cls, config["setting"])
        # Official engine stores daily history in (datetime, vt_symbol) keys.
        # Direct CSV injection avoids modifying strategies or global vn.py databases.
        for row in panel.itertuples(index=False):
            symbol, exchange = row.symbol.rsplit(".", 1)
            dt = pd.Timestamp(row.date).to_pydatetime()
            bar = BarData(symbol=symbol, exchange=Exchange(exchange), datetime=dt,
                interval=Interval.DAILY, open_price=row.open, high_price=row.high,
                low_price=row.low, close_price=row.close, gateway_name="LOCAL_CSV")
            engine.history_data[(dt, row.symbol)] = bar
            engine.dts.add(dt)
        output = prepare_output(args.output)
        with run_log(output):
            engine.run_backtesting()
            if engine.datetime != max(engine.dts):
                raise ValueError("Native replay ended before last input date; inspect run.log")
            daily = engine.calculate_result()
            if daily is None or daily.empty:
                raise ValueError("Native engine returned no results; inspect initialization and trades")
            statistics = engine.calculate_statistics(daily, output=False)
        # Native statistics populate balance; do not recalculate native annual metrics.
        results = daily.reset_index().rename(columns={"date": "timestamp", "balance": "equity"})
        trades = [{"timestamp": t.datetime, "symbol": t.vt_symbol, "direction": t.direction.value,
                   "offset": t.offset.value, "price": t.price, "volume": t.volume}
                  for t in engine.trades.values()]
        daily.to_csv(output / "native_daily.csv", encoding="utf-8-sig")
        (output / "native_statistics.json").write_text(json.dumps(statistics,
            ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        export_run(ROOT, output, results, trades, config["capital"], {
            "project": PROJECT, "accent": "#7855d4", "demo": args.demo,
            "data_kind": "SYNTHETIC DEMO DATA / native vn.py" if args.demo else "User-supplied daily CSV / native vn.py",
            "engine": "Native vnpy_portfoliostrategy.BacktestingEngine",
            "parameters": vars(args), "profile": config,
            "terminal_positions": {s: engine.strategy.get_pos(s) for s in symbols},
            "execution_note": "Original strategy plus native vn.py initialization and matching. "
                              "Daily CSV injected into native history_data; no GUI or database. "
                              "See native_statistics.json for native metrics.",
        }, [price_path, args.config])
    except (ValueError, FileNotFoundError) as e:
        p.error(str(e))


if __name__ == "__main__":
    main()

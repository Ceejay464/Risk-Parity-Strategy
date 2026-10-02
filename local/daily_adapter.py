"""Minimal daily replay adapter for ORIGINAL strategy classes.

This is deliberately not a replacement for vn.py. It supports only the APIs
used in the two bundled strategy files; no broker, tick, database or GUI support.
Synthetic fixtures demonstrate the strategy callbacks, not historical returns.
"""
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import ModuleType
import importlib.util
import sys
import numpy as np
import pandas as pd


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


class Offset(Enum):
    OPEN = "open"
    CLOSE = "close"


@dataclass
class BarData:
    vt_symbol: str
    datetime: object
    open_price: float
    high_price: float
    low_price: float
    close_price: float


@dataclass
class TradeData:
    vt_symbol: str
    direction: Direction
    price: float
    volume: int
    datetime: object


class ArrayManager:
    def __init__(self, size=100):
        self.size = size
        self.count = 0
        self.inited = False
        self.close = np.zeros(size, dtype=float)

    def update_bar(self, bar):
        self.close[:-1] = self.close[1:]
        self.close[-1] = bar.close_price
        self.count += 1
        self.inited = self.count >= self.size


class PortfolioBarGenerator:
    def __init__(self, callback):
        self.callback = callback

    def update_tick(self, tick):
        raise NotImplementedError("Daily adapter does not support tick replay")


class StrategyTemplate:
    def __init__(self, engine, name, symbols, setting):
        self.strategy_engine = engine
        self.strategy_name = name
        self.vt_symbols = list(symbols)
        self.pos_data = defaultdict(int)
        self.target_data = defaultdict(int)
        self.trading = False
        self.inited = False
        for key, value in setting.items():
            if key not in self.parameters:
                raise ValueError(f"Unknown strategy setting: {key}")
            setattr(self, key, value)

    def get_pos(self, symbol):
        return self.pos_data[symbol]

    def get_size(self, symbol):
        return 1

    def set_target(self, symbol, target):
        self.target_data[symbol] = int(target)

    def load_bars(self, days):
        self.strategy_engine.warmup_days = days

    def put_event(self):
        pass

    def write_log(self, message):
        print(message)

    def update_trade(self, trade):
        sign = 1 if trade.direction == Direction.LONG else -1
        self.pos_data[trade.vt_symbol] += sign * trade.volume

    def rebalance_portfolio(self, bars):
        if not self.trading:
            return
        # Replace unfilled orders only when the original strategy requests rebalance.
        self.strategy_engine.pending = []
        for symbol, bar in bars.items():
            delta = self.target_data[symbol] - self.get_pos(symbol)
            if delta:
                direction = Direction.LONG if delta > 0 else Direction.SHORT
                price = self.calculate_price(symbol, direction, bar.close_price)
                self.strategy_engine.pending.append({
                    "symbol": symbol, "quantity": delta,
                    "limit": round(price / 0.001) * 0.001,
                    "signal_date": str(bar.datetime.date()),
                })


def install_compatibility_modules():
    """Only call in a dedicated demo process, never inside a live vn.py process."""
    names = ["vnpy", "vnpy.trader", "vnpy.trader.constant", "vnpy.trader.object",
             "vnpy.trader.utility", "vnpy_portfoliostrategy", "vnpy_portfoliostrategy.utility"]
    if any(name in sys.modules for name in names):
        raise RuntimeError("Run the adapter in a separate Python process; vn.py is already imported")
    for name in names:
        module = ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    sys.modules["vnpy.trader.constant"].Direction = Direction
    sys.modules["vnpy.trader.constant"].Offset = Offset
    obj = sys.modules["vnpy.trader.object"]
    obj.BarData, obj.TradeData, obj.TickData = BarData, TradeData, object
    sys.modules["vnpy.trader.utility"].ArrayManager = ArrayManager
    pkg = sys.modules["vnpy_portfoliostrategy"]
    pkg.StrategyTemplate, pkg.StrategyEngine = StrategyTemplate, object
    sys.modules["vnpy_portfoliostrategy.utility"].PortfolioBarGenerator = PortfolioBarGenerator


def load_strategy(path, name):
    spec = importlib.util.spec_from_file_location("original_strategy", Path(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


class DailyReplay:
    def __init__(self, capital, rate=0.0003, slippage=0.001):
        self.cash = float(capital)
        self.rate = rate
        self.slippage = slippage  # absolute price units per ETF share
        self.pending = []
        self.warmup_days = 0
        self.trades = []
        self.state_history = []

    def fill_orders(self, strategy, bars):
        remaining = []
        for order in self.pending:
            bar = bars[order["symbol"]]
            delta, limit = order["quantity"], order["limit"]
            crossed = (limit >= bar.low_price and bar.low_price > 0 if delta > 0 else
                       limit <= bar.high_price and bar.high_price > 0)
            if not crossed:
                remaining.append(order)
                continue
            price = min(limit, bar.open_price) if delta > 0 else max(limit, bar.open_price)
            commission = abs(delta * price) * self.rate
            slippage_cost = abs(delta) * self.slippage
            self.cash -= delta * price + commission + slippage_cost
            trade = TradeData(order["symbol"], Direction.LONG if delta > 0 else Direction.SHORT,
                              price, abs(delta), bar.datetime)
            # Original override calls the base updater, then its own cash accounting.
            strategy.update_trade(trade)
            self.trades.append({"timestamp": bar.datetime, "symbol": order["symbol"],
                "quantity": delta, "price": price, "commission": commission,
                "slippage_cost": slippage_cost, "limit": limit,
                "signal_date": order["signal_date"]})
        self.pending = remaining

    def run(self, strategy_cls, panel, setting):
        strategy = strategy_cls(self, "local_demo", sorted(panel["symbol"].unique()), setting)
        strategy.on_init()
        results = []
        grouped = list(panel.groupby("date", sort=True))
        if len(grouped) <= self.warmup_days:
            raise ValueError(f"Need more than {self.warmup_days} dates for initialization")
        for index, (day, rows) in enumerate(grouped):
            bars = {r.symbol: BarData(r.symbol, pd.Timestamp(day).to_pydatetime(),
                     r.open, r.high, r.low, r.close) for r in rows.itertuples(index=False)}
            if index == self.warmup_days:
                strategy.inited = True
                strategy.on_start()
                strategy.trading = True
            if strategy.trading:
                self.fill_orders(strategy, bars)
            strategy.on_bars(bars)
            ledger_equity = self.cash + sum(strategy.get_pos(s) * b.close_price for s, b in bars.items())
            results.append({"timestamp": day, "equity": ledger_equity,
                "cash": self.cash, "warmup": not strategy.trading,
                "strategy_internal_equity": getattr(strategy, "total_equity", None)})
            self.state_history.append({"timestamp": str(day),
                "positions": dict(strategy.pos_data), "targets": dict(strategy.target_data),
                "is_stopped": getattr(strategy, "is_stopped", None),
                "market_trend": getattr(strategy, "market_trend", None),
                "target_weights": dict(getattr(strategy, "target_weights", {})),
                "avg_price": dict(getattr(strategy, "avg_price", {})),
                "target_reached": dict(getattr(strategy, "target_reached", {}))})
        strategy.on_stop()
        return pd.DataFrame(results), strategy

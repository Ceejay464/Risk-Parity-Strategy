"""Original strategy behavior in the explicitly isolated compatibility process."""
from datetime import datetime
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import subprocess
import sys
import unittest
import numpy as np

from local.daily_adapter import (install_compatibility_modules, load_strategy,
    DailyReplay, BarData, TradeData, Direction)
from local.run import ROOT, SOURCE, CLASS_NAME


class OriginalStrategyBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_compatibility_modules()
        cls.strategy_cls = load_strategy(SOURCE, CLASS_NAME)

    def strategy(self, settings=None):
        return self.strategy_cls(DailyReplay(1_000_000), "test", ["510300.SSE", "511010.SSE"], settings or {})

    def test_native_entrypoint_help_without_importing_vnpy(self):
        result = subprocess.run([sys.executable, "-m", "local.run_vnpy", "--help"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_original_trade_callback_updates_positions_and_cash(self):
        strategy = self.strategy({"initial_capital": 1000, "commission_rate": 0.0003})
        trade = TradeData("510300.SSE", Direction.LONG, 2, 100, datetime(2023, 1, 2))
        strategy.update_trade(trade)
        self.assertEqual(strategy.get_pos("510300.SSE"), 100)
        self.assertAlmostEqual(strategy.current_capital, 799.94)
        strategy.update_trade(TradeData("510300.SSE", Direction.SHORT, 3, 100, datetime(2023, 1, 3)))
        self.assertEqual(strategy.get_pos("510300.SSE"), 0)
        self.assertAlmostEqual(strategy.current_capital, 1099.85)

    def test_risk_parity_weights_balance_actual_risk_contributions(self):
        strategy = self.strategy({"risk_parity_lookback": 60, "risk_parity_max_iter": 1000})
        rng = np.random.default_rng(7)
        ret1 = rng.normal(0.0002, 0.006, 300)
        ret2 = rng.normal(0.0001, 0.002, 300) + ret1 * 0.15
        for symbol, returns in zip(strategy.vt_symbols, [ret1, ret2]):
            am = strategy.ams[symbol]
            am.close[:] = 10 * np.cumprod(1 + returns)
            am.inited = True
        with redirect_stdout(StringIO()):
            weights = strategy.calculate_risk_parity_weights()
        ordered = [weights[s] for s in strategy.vt_symbols]
        returns = np.column_stack([
            am.close[-60:] / am.close[-61:-1] - 1 for am in strategy.ams.values()])
        cov = np.cov(returns.T) * 252
        cov += np.eye(2) * np.diag(cov).mean() * 1e-4
        w = np.array(ordered)
        rc = w * (cov @ w) / np.sqrt(w @ cov @ w)
        self.assertAlmostEqual(w.sum(), 1)
        self.assertTrue((w > 0).all())
        self.assertLess(np.ptp(rc), 1e-4)

    def test_array_manager_requires_300_updates(self):
        strategy = self.strategy()
        am = strategy.ams["510300.SSE"]
        bar = BarData("510300.SSE", datetime(2023, 1, 2), 1, 1, 1, 1)
        for _ in range(299):
            am.update_bar(bar)
        self.assertFalse(am.inited)
        am.update_bar(bar)
        self.assertTrue(am.inited)



if __name__ == "__main__":
    unittest.main()

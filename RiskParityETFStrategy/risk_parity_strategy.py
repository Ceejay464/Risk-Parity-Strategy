from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional

import numpy as np

from vnpy.trader.utility import ArrayManager
from vnpy.trader.object import TickData, BarData, TradeData
from vnpy.trader.constant import Direction, Offset

from vnpy_portfoliostrategy import StrategyTemplate, StrategyEngine
from vnpy_portfoliostrategy.utility import PortfolioBarGenerator


class EnhancedRiskParityStrategy(StrategyTemplate):
    """增强版风险平价策略 - 动态权重 + 波动率目标 + 真实风险平价"""

    author = "EnhancedRiskParity"

    # ========== 策略参数 ==========
    # 调仓频率
    rebalance_interval = 21  # 月度调仓

    # 动态权重参数（基于波动率）
    use_dynamic_weights = True  # 启用动态权重
    volatility_lookback = 60  # 波动率计算窗口
    target_portfolio_vol = 0.08  # 目标组合波动率8%

    # 市场状态判断
    use_market_regime = True  # 启用市场状态判断
    ma_trend_lookback = 200  # 均线趋势判断窗口

    # 风险平价参数（升级版）
    use_risk_parity = True  # 启用风险平价（否则用固定权重）
    risk_parity_lookback = 60  # 协方差矩阵窗口
    risk_parity_max_iter = 100  # 风险平价最大迭代次数
    risk_parity_tolerance = 1e-6  # 风险平价收敛精度

    # 仓位管理
    max_position_pct = 0.95  # 最大总仓位95%
    min_position_pct = 0.40  # 最小总仓位40%
    single_etf_max_pct = 0.50  # 单只ETF最大持仓比例
    use_full_capital = True  # 是否使用全部资金（True=动态现金管理，False=直接缩放权重）

    # 风险控制
    max_drawdown_stop = 0.18  # 最大回撤止损线18%
    trailing_stop = 0.10  # 移动止损10%
    stop_loss_days = 20  # 止损后冷却天数

    # 动态止损（权益创新高后收紧止损）
    use_dynamic_stop = True  # 启用动态止损
    peak_multiplier = 0.5  # 创新高后止损收紧倍数

    # 市场状态调整系数（优化版）
    bullish_equity_multiplier = 1.2  # 牛市中股票权重倍数
    bullish_bond_multiplier = 0.8  # 牛市中债券权重倍数
    bearish_equity_multiplier = 0.7  # 熊市中股票权重倍数
    bearish_gold_multiplier = 1.4  # 熊市中黄金权重倍数
    bearish_bond_multiplier = 1.1  # 熊市中债券权重倍数

    # 再平衡阈值
    rebalance_threshold = 0.10  # 权重偏离超过10%才调仓

    # 基础参数
    price_add = 0.01
    initial_capital = 1_000_000

    # 成交成本：这里用于策略内部现金估算，要和回测引擎设置尽量一致
    commission_rate = 0.0003

    # ========== 策略变量 ==========
    current_weights: Dict[str, float] = {}
    target_weights: Dict[str, float] = {}
    last_rebalance_date: Optional[datetime] = None
    peak_equity: float = 0.0
    peak_equity_date: Optional[datetime] = None
    is_stopped: bool = False
    stop_start_date: Optional[datetime] = None
    market_trend: str = "neutral"  # bullish, bearish, neutral
    current_volatility: float = 0.0
    current_risk_scale: float = 1.0  # 当前风险缩放因子

    # 记录历史权益
    equity_history: List[float] = []
    daily_returns: List[float] = []

    parameters = [
        "rebalance_interval",
        "use_dynamic_weights",
        "volatility_lookback",
        "target_portfolio_vol",
        "use_market_regime",
        "ma_trend_lookback",
        "use_risk_parity",
        "risk_parity_lookback",
        "risk_parity_max_iter",
        "risk_parity_tolerance",
        "max_position_pct",
        "min_position_pct",
        "single_etf_max_pct",
        "use_full_capital",
        "max_drawdown_stop",
        "trailing_stop",
        "stop_loss_days",
        "use_dynamic_stop",
        "peak_multiplier",
        "rebalance_threshold",
        "bullish_equity_multiplier",
        "bullish_bond_multiplier",
        "bearish_equity_multiplier",
        "bearish_gold_multiplier",
        "bearish_bond_multiplier",
        "price_add",
        "initial_capital",
        "commission_rate",
    ]

    variables = [
        "current_weights",
        "target_weights",
        "market_trend",
        "current_volatility",
        "is_stopped",
        "current_risk_scale",
        "current_capital",
        "total_equity",
        "peak_equity",
    ]

    def __init__(
        self,
        strategy_engine: StrategyEngine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)

        # 存储ArrayManager
        self.ams: Dict[str, ArrayManager] = {}
        for vt_symbol in self.vt_symbols:
            self.ams[vt_symbol] = ArrayManager(size=300)

        self.current_weights: Dict[str, float] = {}
        self.target_weights: Dict[str, float] = {}
        self.last_rebalance_date: Optional[datetime] = None
        self.last_date: Optional[date] = None

        # 资金管理：这是策略内部估算资金，用于仓位计算。
        # 注意：必须通过 update_trade 更新，不能依赖 on_trade。
        self.current_capital: float = float(self.initial_capital)
        self.total_equity: float = float(self.initial_capital)
        self.peak_equity: float = float(self.initial_capital)
        self.peak_equity_date: Optional[datetime] = None
        self.is_stopped: bool = False
        self.stop_start_date: Optional[datetime] = None

        # 历史记录
        self.equity_history: List[float] = []
        self.daily_returns: List[float] = []

        # 市场状态
        self.market_trend: str = "neutral"
        self.current_volatility: float = 0.0
        self.current_risk_scale: float = 1.0

        # 资产分类
        self.asset_groups: Dict[str, str] = {}
        self._classify_assets()

        self.pbg = PortfolioBarGenerator(self.on_bars)

    def _classify_assets(self) -> None:
        """资产分类"""
        for vt_symbol in self.vt_symbols:
            code = vt_symbol.split(".")[0]

            if code in ["510050", "510300", "510500", "159915", "510310", "510330"]:
                self.asset_groups[vt_symbol] = "equity"
            elif code in ["511010", "511260", "511880", "019547"]:
                self.asset_groups[vt_symbol] = "bond"
            elif code in ["518880", "159937", "159612"]:
                self.asset_groups[vt_symbol] = "gold"
            elif code in ["513100", "159920", "513050"]:
                self.asset_groups[vt_symbol] = "overseas"
            else:
                self.asset_groups[vt_symbol] = "other"

    def on_init(self) -> None:
        self.write_log(f"增强版风险平价策略初始化，初始资金: {self.initial_capital:.2f}")
        self.write_log(f"资金管理模式: {'动态现金管理' if self.use_full_capital else '直接缩放权重'}")
        self.load_bars(max(self.volatility_lookback, self.ma_trend_lookback, self.risk_parity_lookback, 100))

    def on_start(self) -> None:
        self.write_log("策略启动")

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_tick(self, tick: TickData) -> None:
        self.pbg.update_tick(tick)

    def update_trade(self, trade: TradeData) -> None:
        """
        成交更新。

        重要修复：
        PortfolioStrategy回测里不要依赖 on_trade。
        这里重载 update_trade，先调用父类，确保 get_pos 正常更新；
        然后更新策略内部现金账本。
        """
        super().update_trade(trade)

        size = self.get_size(trade.vt_symbol)
        trade_value = trade.price * trade.volume * size
        commission = abs(trade_value) * self.commission_rate

        # 对ETF/股票这类净持仓品种：
        # 买入(Direction.LONG) = 花现金
        # 卖出(Direction.SHORT) = 收现金
        if trade.direction == Direction.LONG:
            self.current_capital -= trade_value
        elif trade.direction == Direction.SHORT:
            self.current_capital += trade_value

        self.current_capital -= commission

    def calculate_price(self, vt_symbol: str, direction: Direction, reference: float) -> float:
        """
        计算委托价格。

        原代码里的 price_add 没有生效，这里补上。
        买入适当加价，卖出适当减价，提高成交概率。
        """
        if direction == Direction.LONG:
            return reference + self.price_add
        else:
            return max(reference - self.price_add, 0.01)

    # ========== 核心：动态权重计算 ==========
    def calculate_volatility(self, am: ArrayManager) -> float:
        """计算年化波动率"""
        if not am.inited or len(am.close) < self.volatility_lookback + 1:
            return 0.16  # 默认16%波动率

        closes = np.asarray(am.close[-self.volatility_lookback - 1:], dtype=float)
        if np.any(closes <= 0):
            return 0.16

        returns = closes[1:] / closes[:-1] - 1
        returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)

        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        return max(0.05, min(0.40, annual_vol))  # 限制在5%-40%

    def calculate_inverse_vol_weights(self) -> Dict[str, float]:
        """波动率倒数加权（备用方案，不考虑相关性）"""
        volatilities = {}

        for vt_symbol, am in self.ams.items():
            if not am.inited:
                continue

            vol = self.calculate_volatility(am)
            if vol > 0:
                volatilities[vt_symbol] = vol

        if not volatilities:
            return {}

        inv_vol = {k: 1.0 / v for k, v in volatilities.items()}
        total = sum(inv_vol.values())

        if total <= 0:
            return {}

        weights = {k: v / total for k, v in inv_vol.items()}
        return weights

    def calculate_risk_parity_weights(self) -> Dict[str, float]:
        """
        风险平价优化（考虑相关性）

        修复点：
        1. 对协方差矩阵做正则化；
        2. 对风险贡献为负/异常的情况做保护；
        3. 使用带阻尼的乘法更新，减少权重震荡；
        4. 不收敛时保留最后一组有效权重，而不是报错中断。
        """
        if not self.use_risk_parity:
            return self.calculate_inverse_vol_weights()

        returns_list = []
        valid_symbols = []

        for vt_symbol, am in self.ams.items():
            if not am.inited or len(am.close) < self.risk_parity_lookback + 1:
                continue

            closes = np.asarray(am.close[-self.risk_parity_lookback - 1:], dtype=float)
            if np.any(closes <= 0):
                continue

            rets = closes[1:] / closes[:-1] - 1
            rets = np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=0.0)

            if len(rets) != self.risk_parity_lookback:
                continue

            returns_list.append(rets)
            valid_symbols.append(vt_symbol)

        if len(valid_symbols) < 2:
            return self.calculate_inverse_vol_weights()

        returns_array = np.column_stack(returns_list)

        try:
            cov_matrix = np.cov(returns_array.T) * 252

            if cov_matrix.ndim == 0:
                return self.calculate_inverse_vol_weights()

            # 正则化，避免奇异矩阵
            avg_var = np.mean(np.diag(cov_matrix))
            if not np.isfinite(avg_var) or avg_var <= 0:
                avg_var = 1e-4

            cov_matrix = cov_matrix + np.eye(len(valid_symbols)) * avg_var * 1e-4
            cov_matrix = np.nan_to_num(cov_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        except Exception as e:
            self.write_log(f"协方差矩阵计算失败: {e}，使用简化版")
            return self.calculate_inverse_vol_weights()

        n_assets = len(valid_symbols)
        weights = np.ones(n_assets) / n_assets

        converged = False

        for iteration in range(self.risk_parity_max_iter):
            weights_old = weights.copy()

            cov_w = cov_matrix @ weights
            portfolio_var = weights @ cov_w

            if not np.isfinite(portfolio_var) or portfolio_var <= 1e-12:
                self.write_log("组合方差异常，使用简化版波动率倒数权重")
                return self.calculate_inverse_vol_weights()

            portfolio_vol = np.sqrt(portfolio_var)

            # 风险贡献：RC_i = w_i * (Σw)_i / σ
            risk_contrib = weights * cov_w / portfolio_vol

            if np.any(~np.isfinite(risk_contrib)):
                return self.calculate_inverse_vol_weights()

            # 出现负风险贡献时，说明协方差结构不适合这个简单迭代，回退到倒数波动率
            if np.any(risk_contrib <= 0):
                self.write_log("风险贡献出现非正值，使用简化版波动率倒数权重")
                return self.calculate_inverse_vol_weights()

            target_risk = np.mean(risk_contrib)
            if target_risk <= 0 or not np.isfinite(target_risk):
                return self.calculate_inverse_vol_weights()

            # 收敛条件：风险贡献接近相等
            rc_error = np.max(np.abs(risk_contrib - target_risk))
            if rc_error < self.risk_parity_tolerance:
                converged = True
                self.write_log(f"风险平价迭代收敛，共{iteration + 1}次迭代")
                break

            # 带阻尼的乘法更新，避免原版 target/risk_contrib 过度震荡
            update_ratio = np.sqrt(target_risk / risk_contrib)
            update_ratio = np.clip(update_ratio, 0.5, 2.0)

            weights = weights * update_ratio
            weights = np.maximum(weights, 1e-8)
            weights = weights / np.sum(weights)

            if np.max(np.abs(weights - weights_old)) < self.risk_parity_tolerance:
                converged = True
                self.write_log(f"风险平价权重收敛，共{iteration + 1}次迭代")
                break

        if not converged:
            self.write_log("风险平价未完全收敛，使用最后一组有效权重")

        weights = np.maximum(weights, 0)
        weight_sum = np.sum(weights)

        if weight_sum <= 0 or not np.isfinite(weight_sum):
            return self.calculate_inverse_vol_weights()

        weights = weights / weight_sum

        result = {valid_symbols[i]: float(weights[i]) for i in range(n_assets)}
        return result

    def apply_market_regime(self, weights: Dict[str, float]) -> Dict[str, float]:
        """根据市场状态调整权重（优化版，避免剧烈变化）"""
        if not self.use_market_regime:
            return weights

        self.detect_market_trend()

        adjusted_weights = weights.copy()

        if self.market_trend == "bullish":
            # 牛市中：提高股票权重，降低债券权重
            for vt_symbol in list(adjusted_weights.keys()):
                asset_type = self.asset_groups.get(vt_symbol, "other")

                if asset_type == "equity":
                    adjusted_weights[vt_symbol] *= self.bullish_equity_multiplier
                elif asset_type == "bond":
                    adjusted_weights[vt_symbol] *= self.bullish_bond_multiplier

        elif self.market_trend == "bearish":
            # 熊市中：降低股票权重，提高黄金和债券权重
            for vt_symbol in list(adjusted_weights.keys()):
                asset_type = self.asset_groups.get(vt_symbol, "other")

                if asset_type == "equity":
                    adjusted_weights[vt_symbol] *= self.bearish_equity_multiplier
                elif asset_type == "gold":
                    adjusted_weights[vt_symbol] *= self.bearish_gold_multiplier
                elif asset_type == "bond":
                    adjusted_weights[vt_symbol] *= self.bearish_bond_multiplier

        # 重新归一化
        total = sum(adjusted_weights.values())
        if total > 0:
            adjusted_weights = {k: v / total for k, v in adjusted_weights.items()}

        return adjusted_weights

    def detect_market_trend(self) -> None:
        """检测市场趋势"""
        benchmark = None

        # 优先使用沪深300ETF
        for vt_symbol in self.vt_symbols:
            if "510300" in vt_symbol:
                benchmark = self.ams[vt_symbol]
                break

        # 如果没有510300，退而求其次使用第一只权益类资产
        if benchmark is None:
            for vt_symbol in self.vt_symbols:
                if self.asset_groups.get(vt_symbol) == "equity":
                    benchmark = self.ams[vt_symbol]
                    break

        if benchmark is None or not benchmark.inited:
            self.market_trend = "neutral"
            return

        if len(benchmark.close) >= self.ma_trend_lookback:
            closes = np.asarray(benchmark.close, dtype=float)
            if np.any(closes[-self.ma_trend_lookback:] <= 0):
                self.market_trend = "neutral"
                return

            ma_long = np.mean(closes[-self.ma_trend_lookback:])
            ma_short = np.mean(closes[-20:])
            current_price = closes[-1]

            if current_price > ma_short > ma_long:
                self.market_trend = "bullish"
            elif current_price < ma_short < ma_long:
                self.market_trend = "bearish"
            else:
                self.market_trend = "neutral"
        else:
            self.market_trend = "neutral"

    def apply_volatility_target(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        波动率目标调整（修正版）

        use_full_capital=True:
            权重本身保持归一化，风险缩放通过 current_risk_scale 在目标仓位里体现。

        use_full_capital=False:
            权重直接缩放成目标仓位比例。
        """
        if not weights:
            self.current_risk_scale = 1.0
            return {}

        if not self.use_dynamic_weights:
            self.current_risk_scale = 1.0

            if not self.use_full_capital:
                total_position = self.max_position_pct
                total_position = max(self.min_position_pct, min(self.max_position_pct, total_position))
                return {k: v * total_position for k, v in weights.items()}

            return weights.copy()

        portfolio_vol = self.calculate_portfolio_volatility(weights)
        self.current_volatility = portfolio_vol

        if portfolio_vol > self.target_portfolio_vol and portfolio_vol > 0:
            scale = self.target_portfolio_vol / portfolio_vol
            scale = max(0.5, min(1.0, scale))  # 限制最大降幅50%
        else:
            scale = 1.0

        self.current_risk_scale = scale

        if self.use_full_capital:
            adjusted_weights = weights.copy()
        else:
            total_position = self.max_position_pct * scale
            total_position = max(self.min_position_pct, min(self.max_position_pct, total_position))
            adjusted_weights = {k: v * total_position for k, v in weights.items()}

        return adjusted_weights

    def calculate_portfolio_volatility(self, weights: Dict[str, float]) -> float:
        """计算组合预期波动率"""
        if len(weights) < 2:
            return 0.16

        returns_list = []
        valid_symbols = []

        lookback = min(60, self.risk_parity_lookback)

        for vt_symbol, w in weights.items():
            if w <= 0:
                continue

            am = self.ams.get(vt_symbol)
            if not am or not am.inited or len(am.close) < lookback + 1:
                continue

            closes = np.asarray(am.close[-lookback - 1:], dtype=float)
            if np.any(closes <= 0):
                continue

            rets = closes[1:] / closes[:-1] - 1
            rets = np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=0.0)

            if len(rets) != lookback:
                continue

            returns_list.append(rets)
            valid_symbols.append(vt_symbol)

        if len(valid_symbols) < 2:
            return 0.16

        try:
            returns_array = np.column_stack(returns_list)
            cov_matrix = np.cov(returns_array.T) * 252
            cov_matrix = np.nan_to_num(cov_matrix, nan=0.0, posinf=0.0, neginf=0.0)

            weight_array = np.array([weights[s] for s in valid_symbols], dtype=float)
            weight_sum = np.sum(weight_array)

            if weight_sum <= 0:
                return 0.16

            # 这里按归一化权重估算组合自身波动率，
            # 仓位缩放在 calculate_target_positions 中体现。
            weight_array = weight_array / weight_sum

            portfolio_var = weight_array @ cov_matrix @ weight_array

            if portfolio_var <= 0 or not np.isfinite(portfolio_var):
                return 0.16

            portfolio_vol = np.sqrt(portfolio_var)

        except Exception as e:
            self.write_log(f"组合波动率计算失败: {e}")
            return 0.16

        return max(0.05, min(0.40, float(portfolio_vol)))

    # ========== 风险控制 ==========
    def check_risk_controls(self, total_equity: float, current_datetime: datetime) -> bool:
        """增强版风险控制"""
        if total_equity <= 0:
            self.write_log("总权益小于等于0，触发风控")
            return True

        # 冷却期检查
        if self.is_stopped and self.stop_start_date:
            days_passed = (current_datetime - self.stop_start_date).days

            if days_passed < self.stop_loss_days:
                return True
            else:
                self.is_stopped = False
                self.peak_equity = total_equity
                self.peak_equity_date = current_datetime
                self.equity_history = []
                self.write_log("止损冷却期结束，恢复交易")
                return False

        # 更新权益峰值
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity
            self.peak_equity_date = current_datetime

        # 计算当前回撤
        drawdown = (self.peak_equity - total_equity) / self.peak_equity if self.peak_equity > 0 else 0

        # 动态止损阈值
        stop_threshold = self.max_drawdown_stop

        if self.use_dynamic_stop and self.peak_equity_date:
            days_since_peak = (current_datetime - self.peak_equity_date).days

            if days_since_peak < 30:
                stop_threshold = self.max_drawdown_stop * self.peak_multiplier

        # 检查最大回撤止损
        if drawdown > stop_threshold:
            self.write_log(f"触发最大回撤止损: {drawdown:.2%} > {stop_threshold:.2%}")
            return True

        # 检查移动止损
        if len(self.equity_history) >= 10:
            max_equity_recent = max(self.equity_history[-10:])
            trailing_drawdown = (
                (max_equity_recent - total_equity) / max_equity_recent
                if max_equity_recent > 0
                else 0
            )

            if trailing_drawdown > self.trailing_stop:
                self.write_log(f"触发移动止损: {trailing_drawdown:.2%} > {self.trailing_stop:.2%}")
                return True

        # 更新历史
        self.equity_history.append(total_equity)
        if len(self.equity_history) > 50:
            self.equity_history.pop(0)

        return False

    def update_total_equity(self, bars: Dict[str, BarData]) -> float:
        """更新总权益"""
        # 重要修复：不能 max(0, current_capital)，负现金必须反映为负债
        cash = self.current_capital
        position_value = 0.0

        for vt_symbol, bar in bars.items():
            pos = self.get_pos(vt_symbol)
            if pos != 0:
                size = self.get_size(vt_symbol)
                position_value += pos * bar.close_price * size

        self.total_equity = cash + position_value

        if self.total_equity <= 0:
            self.write_log(
                f"权益异常: cash={cash:.2f}, position_value={position_value:.2f}, "
                f"total_equity={self.total_equity:.2f}"
            )
            self.total_equity = 1.0

        return self.total_equity

    def calculate_current_weights(
        self,
        total_equity: float,
        bars: Dict[str, BarData]
    ) -> Dict[str, float]:
        """根据真实持仓市值计算当前权重"""
        current_weights = {}

        if total_equity <= 0:
            return {vt_symbol: 0.0 for vt_symbol in self.vt_symbols}

        for vt_symbol in self.vt_symbols:
            bar = bars.get(vt_symbol)
            if not bar:
                current_weights[vt_symbol] = 0.0
                continue

            pos = self.get_pos(vt_symbol)
            size = self.get_size(vt_symbol)
            market_value = pos * bar.close_price * size
            current_weights[vt_symbol] = market_value / total_equity

        return current_weights

    def need_rebalance(self, current_weights: Dict[str, float], target_weights: Dict[str, float]) -> bool:
        """检查是否需要再平衡"""
        if not target_weights:
            return False

        if not current_weights:
            return True

        symbols = set(current_weights.keys()) | set(target_weights.keys())

        for vt_symbol in symbols:
            current = current_weights.get(vt_symbol, 0)
            target = target_weights.get(vt_symbol, 0)

            # 权重偏离超过阈值
            if abs(current - target) > self.rebalance_threshold:
                return True

        return False

    def calculate_target_positions(
        self,
        total_equity: float,
        weights: Dict[str, float],
        bars: Dict[str, BarData]
    ) -> Dict[str, int]:
        """
        计算目标持仓

        重要修复：
        1. use_full_capital=True 时也必须使用 max_position_pct；
        2. current_risk_scale 只影响总风险暴露；
        3. single_etf_max_pct 限制单只ETF市值；
        4. 目标仓位按bar.close_price估算，真实委托价格由 calculate_price 控制。
        """
        targets = {}

        if total_equity <= 0 or not weights:
            return targets

        total_weight = sum(w for w in weights.values() if w > 0)

        if total_weight <= 0:
            return targets

        if self.use_full_capital:
            if self.use_dynamic_weights:
                total_position_pct = self.max_position_pct * self.current_risk_scale
            else:
                total_position_pct = self.max_position_pct
        else:
            # use_full_capital=False 时，weights 可能已经被 apply_volatility_target 缩放
            total_position_pct = min(sum(w for w in weights.values() if w > 0), self.max_position_pct)

        total_position_pct = max(self.min_position_pct, min(self.max_position_pct, total_position_pct))

        for vt_symbol, weight in weights.items():
            if weight <= 0:
                continue

            am = self.ams.get(vt_symbol)
            if not am or not am.inited:
                continue

            bar = bars.get(vt_symbol)
            if not bar:
                continue

            price = bar.close_price
            size = self.get_size(vt_symbol)

            if price <= 0 or size <= 0:
                continue

            # 目标市值
            if self.use_full_capital:
                target_value = total_equity * total_position_pct * weight / total_weight
            else:
                # 此模式下weights本身可能代表仓位比例，但仍限制总仓位
                target_value = total_equity * weight

            # 单只ETF限制
            max_single_value = total_equity * self.single_etf_max_pct
            target_value = min(target_value, max_single_value)

            # 防止出现负值或非有限值
            if target_value <= 0 or not np.isfinite(target_value):
                continue

            target_volume = int(target_value / (price * size))

            if target_volume > 0:
                targets[vt_symbol] = target_volume

        return targets

    # ========== 主逻辑 ==========
    def on_bars(self, bars: Dict[str, BarData]) -> None:
        """K线切片回调"""
        if not bars:
            return

        current_bar = list(bars.values())[0]
        current_datetime = current_bar.datetime
        current_date = current_datetime.date()

        # 更新K线数据
        for vt_symbol, bar in bars.items():
            am = self.ams.get(vt_symbol)
            if am:
                am.update_bar(bar)

        # 等待所有资产数据初始化
        if not all(am.inited for am in self.ams.values()):
            return

        # 更新总权益
        total_equity = self.update_total_equity(bars)

        # 用真实持仓计算当前权重
        self.current_weights = self.calculate_current_weights(total_equity, bars)

        # 风险控制
        if self.check_risk_controls(total_equity, current_datetime):
            if not self.is_stopped:
                self.is_stopped = True
                self.stop_start_date = current_datetime
                self.write_log(f"触发风控，清空所有持仓，冷却{self.stop_loss_days}天")

                for vt_symbol in self.vt_symbols:
                    if self.get_pos(vt_symbol) != 0:
                        self.set_target(vt_symbol, 0)

                self.target_weights = {}
                self.rebalance_portfolio(bars)

            self.put_event()
            return

        if self.is_stopped:
            self.put_event()
            return

        # 判断是否需要调仓
        time_rebalance = False

        if self.last_rebalance_date is None:
            time_rebalance = True
        else:
            days_since = (current_datetime - self.last_rebalance_date).days
            if days_since >= self.rebalance_interval:
                time_rebalance = True

        drift_rebalance = False
        if self.target_weights:
            drift_rebalance = self.need_rebalance(self.current_weights, self.target_weights)

        if not time_rebalance and not drift_rebalance:
            self.put_event()
            return

        # 防止同一天重复调仓
        if self.last_date == current_date:
            self.put_event()
            return

        self.last_date = current_date

        # 1. 计算基础权重（风险平价，考虑相关性）
        base_weights = self.calculate_risk_parity_weights()

        if not base_weights:
            self.write_log("权重计算失败，跳过调仓")
            self.put_event()
            return

        # 2. 市场状态调整
        regime_weights = self.apply_market_regime(base_weights)

        # 3. 波动率目标调整
        final_weights = self.apply_volatility_target(regime_weights)

        if not final_weights:
            self.write_log("波动率目标调整后权重为空，跳过调仓")
            self.put_event()
            return

        # 保存目标权重
        self.target_weights = final_weights.copy()

        # 4. 计算目标持仓
        targets = self.calculate_target_positions(total_equity, final_weights, bars)

        if not targets:
            self.write_log("目标仓位计算失败")
            self.put_event()
            return

        # 5. 执行调仓
        rebalance_log = []

        # 平仓
        for vt_symbol in self.vt_symbols:
            current_pos = self.get_pos(vt_symbol)

            if vt_symbol not in targets and current_pos != 0:
                rebalance_log.append(f"平仓 {vt_symbol} ({current_pos}手)")
                self.set_target(vt_symbol, 0)

        # 建仓/调仓
        for vt_symbol, target_vol in targets.items():
            current_pos = self.get_pos(vt_symbol)

            if target_vol != current_pos:
                weight = final_weights.get(vt_symbol, 0)
                rebalance_log.append(
                    f"{vt_symbol}: {current_pos}手 -> {target_vol}手 "
                    f"(目标权重 {weight:.1%})"
                )
                self.set_target(vt_symbol, target_vol)

        if rebalance_log:
            self.write_log("调仓执行: " + "; ".join(rebalance_log))
            self.rebalance_portfolio(bars)

        # 调仓后记录时间，当前权重要等成交后由下一次on_bars按真实持仓更新
        self.last_rebalance_date = current_datetime

        # 日志输出
        risk_info = f"风险缩放: {self.current_risk_scale:.2f}" if self.use_dynamic_weights else ""
        self.write_log(
            f"调仓完成 | 权益: {total_equity:,.0f} | "
            f"现金: {self.current_capital:,.0f} | "
            f"趋势: {self.market_trend} | "
            f"组合波动率: {self.current_volatility:.1%} {risk_info}"
        )

        self.put_event()

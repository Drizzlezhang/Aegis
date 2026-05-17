"""策略回测验证 — 历史验证推荐策略的有效性。"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class BacktestResult:
    """回测结果。"""
    symbol: str
    strategy_type: str
    entry_date: date
    entry_price: float
    exit_date: date | None
    exit_price: float | None
    max_gain_pct: float
    max_drawdown_pct: float
    final_pnl_pct: float | None
    days_held: int
    hit_profit_target: bool
    hit_stop_loss: bool
    risk_reward_actual: float | None


class BacktestValidator:
    """历史回测验证器。
    
    用途:
    1. 验证策略推荐在历史数据上是否有效
    2. 计算策略的 win rate, avg PnL, max drawdown
    3. 为 DecisionScorer 提供对比基准
    
    注意: 历史价格由调用方提供，本类不直接调用 fetcher。
    """

    def validate_strategy(
        self,
        symbol: str,
        strategy_type: str,
        entry_date: date,
        entry_price: float,
        target_pct: float,
        stop_loss_pct: float,
        max_days: int = 90,
        historical_prices: list[float] | None = None,
    ) -> BacktestResult:
        """回测单条策略。
        
        Args:
            historical_prices: 入场日之后的每日收盘价列表
        """
        if not historical_prices or not entry_price:
            return BacktestResult(
                symbol=symbol, strategy_type=strategy_type,
                entry_date=entry_date, entry_price=entry_price,
                exit_date=None, exit_price=None,
                max_gain_pct=0.0, max_drawdown_pct=0.0,
                final_pnl_pct=None, days_held=0,
                hit_profit_target=False, hit_stop_loss=False,
                risk_reward_actual=None,
            )
        
        prices = historical_prices[:max_days]
        max_price = entry_price
        min_price = entry_price
        exit_price = None
        exit_day = None
        hit_target = False
        hit_stop = False
        
        for i, price in enumerate(prices):
            max_price = max(max_price, price)
            min_price = min(min_price, price)
            pnl_pct = (price - entry_price) / entry_price * 100
            
            # 检查止盈
            if pnl_pct >= target_pct:
                exit_price = price
                exit_day = i + 1
                hit_target = True
                break
            
            # 检查止损
            if pnl_pct <= -stop_loss_pct:
                exit_price = price
                exit_day = i + 1
                hit_stop = True
                break
        
        max_gain = (max_price - entry_price) / entry_price * 100
        max_dd = (entry_price - min_price) / entry_price * 100
        
        if exit_price is None:
            # 到期未触及止盈止损
            exit_price = prices[-1]
            exit_day = len(prices)
        
        final_pnl = (exit_price - entry_price) / entry_price * 100
        
        # 风险收益比
        risk_reward = None
        if stop_loss_pct > 0:
            risk_reward = final_pnl / stop_loss_pct
        
        exit_date_val = entry_date + timedelta(days=exit_day) if exit_day else None
        
        return BacktestResult(
            symbol=symbol,
            strategy_type=strategy_type,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date_val,
            exit_price=exit_price,
            max_gain_pct=max_gain,
            max_drawdown_pct=max_dd,
            final_pnl_pct=final_pnl,
            days_held=exit_day or 0,
            hit_profit_target=hit_target,
            hit_stop_loss=hit_stop,
            risk_reward_actual=risk_reward,
        )

    def batch_validate(self, decisions: list[dict]) -> list[BacktestResult]:
        """批量回测多条策略。
        
        Args:
            decisions: [{"symbol", "strategy_type", "entry_date", "entry_price",
                        "target_pct", "stop_loss_pct", "max_days", "historical_prices"}, ...]
        """
        results = []
        for d in decisions:
            result = self.validate_strategy(
                symbol=d["symbol"],
                strategy_type=d["strategy_type"],
                entry_date=d["entry_date"],
                entry_price=d["entry_price"],
                target_pct=d.get("target_pct", 20.0),
                stop_loss_pct=d.get("stop_loss_pct", 10.0),
                max_days=d.get("max_days", 90),
                historical_prices=d.get("historical_prices"),
            )
            results.append(result)
        return results

    def aggregate_stats(self, results: list[BacktestResult]) -> dict:
        """聚合回测统计。"""
        if not results:
            return {"total_trades": 0, "win_rate": 0.0, "avg_pnl_pct": 0.0,
                    "max_drawdown_pct": 0.0, "profit_factor": 0.0, "avg_days_held": 0.0}
        
        completed = [r for r in results if r.final_pnl_pct is not None]
        if not completed:
            return {"total_trades": len(results), "win_rate": 0.0, "avg_pnl_pct": 0.0,
                    "max_drawdown_pct": 0.0, "profit_factor": 0.0, "avg_days_held": 0.0}
        
        wins = [r for r in completed if r.final_pnl_pct > 0]
        losses = [r for r in completed if r.final_pnl_pct <= 0]
        
        total_gains = sum(r.final_pnl_pct for r in wins) if wins else 0
        total_losses = abs(sum(r.final_pnl_pct for r in losses)) if losses else 0
        
        return {
            "total_trades": len(completed),
            "win_rate": len(wins) / len(completed),
            "avg_pnl_pct": sum(r.final_pnl_pct for r in completed) / len(completed),
            "max_drawdown_pct": max(r.max_drawdown_pct for r in completed),
            "profit_factor": total_gains / total_losses if total_losses > 0 else float('inf'),
            "avg_days_held": sum(r.days_held for r in completed) / len(completed),
        }
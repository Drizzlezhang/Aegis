"""Command-line interface for Aegis-Trader."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from src.cli_services import (
    collect_cli_health_report,
    discover_cli_skills,
    run_cli_analysis,
)
from src.config import get_config, reload_config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_scheduler():
    """Create a scheduler instance connected to the persistent jobstore for CLI ops."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from src.config import get_config
    from src.scheduler.engine import _build_jobstores
    config = get_config().scheduler
    jobstores = _build_jobstores()
    return AsyncIOScheduler(jobstores=jobstores, timezone=config.timezone)


async def scheduler_ls() -> None:
    """List all registered scheduler jobs."""
    try:
        sched = _get_scheduler()
        sched.start()
        try:
            jobs = sched.get_jobs()
            if not jobs:
                print("No jobs registered")
                return
            print(f"{'JOB ID':<30} {'NEXT RUN':<30} {'TRIGGER'}")
            print("-" * 80)
            for j in jobs:
                print(f"{j.id:<30} {str(j.next_run_time) if j.next_run_time else 'N/A':<30} {str(j.trigger)}")
        finally:
            sched.shutdown(wait=False)
    except Exception as e:
        print(f"Scheduler not running: {e}")
        sys.exit(1)


async def scheduler_pause(job_id: str) -> None:
    """Pause a scheduler job."""
    try:
        sched = _get_scheduler()
        sched.start()
        try:
            sched.pause_job(job_id)
            print(f"Job '{job_id}' paused")
        finally:
            sched.shutdown(wait=False)
    except Exception as e:
        print(f"Failed to pause job '{job_id}': {e}")
        sys.exit(1)


async def scheduler_resume(job_id: str) -> None:
    """Resume a scheduler job."""
    try:
        sched = _get_scheduler()
        sched.start()
        try:
            sched.resume_job(job_id)
            print(f"Job '{job_id}' resumed")
        finally:
            sched.shutdown(wait=False)
    except Exception as e:
        print(f"Failed to resume job '{job_id}': {e}")
        sys.exit(1)


async def scheduler_trigger(job_id: str) -> None:
    """Manually trigger a scheduler job."""
    from datetime import datetime
    try:
        sched = _get_scheduler()
        sched.start()
        try:
            job = sched.get_job(job_id)
            if job is None:
                print(f"Job '{job_id}' not found")
                sys.exit(1)
            sched.modify_job(job_id, next_run_time=datetime.now())
            print(f"Job '{job_id}' triggered")
        finally:
            sched.shutdown(wait=False)
    except Exception as e:
        print(f"Failed to trigger job '{job_id}': {e}")
        sys.exit(1)


async def scheduler_history() -> None:
    """Show recent scheduler execution history."""
    from src.scheduler.history import get_session, list_history
    try:
        session = get_session()
        items = list_history(session, limit=20)
        session.close()
        if not items:
            print("No execution history")
            return
        print(f"{'ID':<6} {'JOB ID':<30} {'STATUS':<10} {'START':<28} {'DUR(ms)'}")
        print("-" * 90)
        for item in items:
            dur = str(item['duration_ms']) if item['duration_ms'] is not None else '-'
            print(f"{item['id']:<6} {item['job_id']:<30} {item['status']:<10} "
                  f"{item['start_at'] or '':<28} {dur}")
    except Exception as e:
        print(f"Failed to read history: {e}")
        sys.exit(1)


async def run_analysis(
    symbols: list[str],
    analysis_type: str = "full",
    output_format: str = "json",
    output_file: Path | None = None
) -> None:
    """运行分析流程."""
    logger.info(f"开始分析 {len(symbols)} 个标的: {symbols}")

    try:
        processed_count = await run_cli_analysis(
            symbols=symbols,
            output_format=output_format,
            output_file=output_file,
        )
        logger.info(f"分析完成: 处理了 {processed_count} 个标的")
    except Exception as e:
        logger.error(f"分析失败: {e}")
        sys.exit(1)


async def list_skills() -> None:
    """列出所有可用技能."""
    skills = discover_cli_skills()

    if not skills:
        print("未发现任何技能")
        return

    print(f"发现 {len(skills)} 个技能:\n")
    for skill in skills:
        print(f"  • {skill.name}")
        print(f"    类型: {skill.skill_type.value}")
        print(f"    版本: {skill.version}")
        print(f"    描述: {skill.description}")
        if skill.dependencies:
            print(f"    依赖: {', '.join(skill.dependencies)}")
        print()


async def check_health() -> None:
    """检查系统健康状态."""
    print("检查系统健康状态...\n")

    report = collect_cli_health_report()

    if report.config.ok:
        details = report.config.details or {}
        print("✓ 配置加载成功")
        print(f"  环境: {details.get('environment')}")
        print(f"  核心标的: {details.get('core_symbols_count')} 个")
    else:
        print(f"✗ 配置加载失败: {report.config.error}")

    if report.skills.ok:
        details = report.skills.details or {}
        print(f"✓ 技能发现成功: {details.get('count')} 个技能")
    else:
        print(f"✗ 技能发现失败: {report.skills.error}")

    if report.llm.ok:
        print("✓ LLM 客户端初始化成功")
    else:
        print(f"✗ LLM 客户端初始化失败: {report.llm.error}")

    print("\n健康检查完成")


async def show_status() -> None:
    """显示系统状态."""
    config = get_config()

    print("Aegis-Trader 系统状态\n")
    print(f"版本: {config.version}")
    print(f"环境: {config.environment}")
    print(f"调试模式: {config.debug}")
    print(f"日志级别: {config.log_level}")
    print()

    print("数据源配置:")
    print(f"  • Yahoo Finance: {'启用' if config.data_source.yfinance_enabled else '禁用'}")
    print(f"  • Alpha Vantage: {'启用' if config.data_source.alpha_vantage_enabled else '禁用'}")
    print()

    print("LLM 配置:")
    print(f"  • 提供商: {config.llm.provider}")
    print(f"  • 推理模型: {config.llm.reasoning_model}")
    print()

    print("代理配置:")
    print(f"  • 数据采集: {'启用' if config.agent.data_harvester_enabled else '禁用'}")
    print(f"  • 量化大脑: {'启用' if config.agent.quant_brain_enabled else '禁用'}")
    print(f"  • 策略执行: {'启用' if config.agent.strategy_exec_enabled else '禁用'}")
    print(f"  • 记忆系统: {'启用' if config.agent.aegis_memory_enabled else '禁用'}")
    print(f"  • 最大并发: {config.agent.max_concurrent_agents}")
    print()

    print("核心标的:")
    for i, symbol in enumerate(config.core_symbols, 1):
        print(f"  {i:2d}. {symbol}")
    print()


async def reload_config_cmd() -> None:
    """重新加载配置."""
    print("重新加载配置...")
    config = reload_config()
    print(f"配置已重新加载，环境: {config.environment}")


async def run_health_check(args: argparse.Namespace) -> None:
    """运行数据健康自检."""
    from src.cli.health_check import HealthCheckRunner

    config = get_config()
    runner = HealthCheckRunner(config)
    report = await runner.run_all()

    if args.json:
        print(HealthCheckRunner.format_json(report))
    else:
        print(HealthCheckRunner.format_table(report))

    sys.exit(report.exit_code)


async def run_backtest(args: argparse.Namespace) -> None:
    """运行回测."""
    from datetime import date as dt_date

    from src.backtest.report import render_multi_report, render_report
    from src.backtest.runner import BacktestRunner, MultiSymbolRunner

    start_date = dt_date.fromisoformat(args.from_date)
    end_date = dt_date.fromisoformat(args.to_date)
    output_dir = args.output or Path("reports/backtest")

    # Determine symbols
    if args.symbols:
        symbols = args.symbols
    elif args.symbol:
        symbols = [args.symbol]
    else:
        print("Error: --symbol or --symbols is required")
        sys.exit(1)

    # Generate mock OHLCV data for demo
    import random
    random.seed(42)

    def _make_demo_data(sym: str, n_days: int = 60) -> list:
        from dataclasses import dataclass
        from datetime import datetime, timedelta

        @dataclass
        class _Bar:
            timestamp: datetime
            open: float
            high: float
            low: float
            close: float
            volume: int

        price = 100.0 + hash(sym) % 200
        bars = []
        for i in range(n_days):
            change = random.uniform(-2, 2)
            price += change
            if price < 1:
                price = 1
            ts = datetime(start_date.year, start_date.month, 1) + timedelta(days=i)
            bars.append(_Bar(timestamp=ts, open=price - 0.5, high=price + 1, low=price - 1, close=price, volume=10000))
        return bars

    if len(symbols) == 1:
        # Single symbol
        symbol = symbols[0]
        print(f"Running backtest for {symbol} ({start_date} → {end_date})...")

        data = _make_demo_data(symbol)
        runner = BacktestRunner(symbol, start_date, end_date, {"strategy": args.strategy})

        # Progress bar
        try:
            from rich.progress import Progress
            with Progress() as progress:
                task = progress.add_task(f"[cyan]Backtesting {symbol}...", total=len(data))

                def progress_cb(current: int, total: int) -> None:
                    progress.update(task, completed=current)

                result = await runner.run(data, progress_callback=progress_cb)
        except ImportError:
            result = await runner.run(data)

        # Phase attribution
        from src.backtest.phase_attribution import PhaseAttribution
        result.phase_attribution = PhaseAttribution.analyze(result.trades, result.daily_decisions)

        # Render report
        output_path = output_dir / f"{symbol}_{start_date.isoformat()}_{end_date.isoformat()}.html"
        render_report(result, output_path)
        print(f"Report saved to {output_path}")

        # Print summary
        m = result.metrics
        print(f"\n  Total Return: {m.total_return:.2f}%")
        print(f"  Sharpe Ratio: {m.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {m.max_drawdown:.2f}%")
        print(f"  Win Rate:     {m.win_rate:.1f}%")
        print(f"  Total Trades: {m.total_trades}")

        if not args.no_open:
            import webbrowser
            webbrowser.open(f"file://{output_path.absolute()}")

    else:
        # Multi-symbol
        print(f"Running backtest for {len(symbols)} symbols ({start_date} → {end_date})...")

        data_map = {s: _make_demo_data(s) for s in symbols}
        multi = MultiSymbolRunner(symbols, start_date, end_date, max_concurrent=3)

        try:
            from rich.progress import Progress
            with Progress() as progress:
                task = progress.add_task("[cyan]Backtesting...", total=len(symbols))

                def progress_cb(sym: str, current: int, total: int) -> None:
                    pass  # Multi-symbol progress handled by task completion

                results = await multi.run(data_map)
                progress.update(task, completed=len(symbols))
        except ImportError:
            results = await multi.run(data_map)

        # Add phase attribution to each result
        from src.backtest.phase_attribution import PhaseAttribution
        for _sym, r in results.items():
            r.phase_attribution = PhaseAttribution.analyze(r.trades, r.daily_decisions)

        # Render reports
        render_multi_report(results, output_dir)
        print(f"Reports saved to {output_dir}/")

        # Print summary table
        print(f"\n{'Symbol':<8} {'Return':>10} {'Sharpe':>8} {'Max DD':>8} {'Win Rate':>9} {'Trades':>7}")
        print("-" * 55)
        for sym, r in results.items():
            m = r.metrics
            print(f"{sym:<8} {m.total_return:>9.2f}% {m.sharpe_ratio:>7.2f} {m.max_drawdown:>7.2f}% {m.win_rate:>8.1f}% {m.total_trades:>6}")

        if not args.no_open:
            import webbrowser
            first_sym = symbols[0]
            first_path = output_dir / f"{first_sym}_{start_date.isoformat()}_{end_date.isoformat()}.html"
            webbrowser.open(f"file://{first_path.absolute()}")


async def run_walkforward(args: argparse.Namespace) -> None:
    """Run walk-forward backtest."""
    from datetime import date as dt_date

    from src.backtest.report import render_walkforward_report
    from src.backtest.walk_forward import WalkForwardRunner
    from src.models.backtest import WalkForwardConfig

    start_date = dt_date.fromisoformat(args.from_date)
    end_date = dt_date.fromisoformat(args.to_date)

    config = WalkForwardConfig(
        train_window_days=args.train_days,
        test_window_days=args.test_days,
        step_size_days=args.step_days,
        mode=args.mode,
    )

    # Generate demo data
    import random
    random.seed(42)

    from dataclasses import dataclass
    from datetime import datetime, timedelta

    @dataclass
    class _Bar:
        timestamp: datetime
        open: float
        high: float
        low: float
        close: float
        volume: int

    n_days = (end_date - start_date).days + 1
    price = 100.0 + hash(args.symbol) % 200
    data = []
    for i in range(n_days):
        change = random.uniform(-2, 2)
        price += change
        if price < 1:
            price = 1
        ts = datetime(start_date.year, start_date.month, start_date.day) + timedelta(days=i)
        data.append(_Bar(timestamp=ts, open=price - 0.5, high=price + 1, low=price - 1, close=price, volume=10000))

    print(f"Running walk-forward backtest for {args.symbol} ({start_date} → {end_date})")
    print(f"  Mode: {args.mode}, Train: {args.train_days}d, Test: {args.test_days}d, Step: {args.step_days}d")

    runner = WalkForwardRunner(args.symbol, config, {"strategy": args.strategy})
    result = await runner.run(data)

    print(f"\n  Folds: {len(result.folds)}")
    m = result.aggregate_metrics
    print(f"  OOS Total Return: {m.total_return:.2f}%")
    print(f"  OOS Sharpe Ratio: {m.sharpe_ratio:.2f}")
    print(f"  OOS Max Drawdown: {m.max_drawdown:.2f}%")
    print(f"  OOS Win Rate:     {m.win_rate:.1f}%")

    # Render report
    output_path = args.output or Path(f"reports/backtest/wf_{args.symbol}_{start_date.isoformat()}_{end_date.isoformat()}.html")
    render_walkforward_report(result, output_path)
    print(f"Report saved to {output_path}")

    if not args.no_open:
        import webbrowser
        webbrowser.open(f"file://{output_path.absolute()}")


async def run_mc(args: argparse.Namespace) -> None:
    """Run Monte Carlo simulation."""
    from datetime import date as dt_date

    from src.backtest.monte_carlo import MonteCarloSimulator
    from src.backtest.runner import BacktestRunner

    start_date = dt_date.fromisoformat(args.from_date)
    end_date = dt_date.fromisoformat(args.to_date)

    # Generate demo data
    import random
    random.seed(42)

    from dataclasses import dataclass
    from datetime import datetime, timedelta

    @dataclass
    class _Bar:
        timestamp: datetime
        open: float
        high: float
        low: float
        close: float
        volume: int

    n_days = (end_date - start_date).days + 1
    price = 100.0 + hash(args.symbol) % 200
    data = []
    for i in range(n_days):
        change = random.uniform(-2, 2)
        price += change
        if price < 1:
            price = 1
        ts = datetime(start_date.year, start_date.month, start_date.day) + timedelta(days=i)
        data.append(_Bar(timestamp=ts, open=price - 0.5, high=price + 1, low=price - 1, close=price, volume=10000))

    print(f"Running Monte Carlo simulation for {args.symbol} ({start_date} → {end_date})")
    print(f"  Iterations: {args.iterations}")

    runner = BacktestRunner(args.symbol, start_date, end_date, {"strategy": args.strategy})
    result = await runner.run(data)

    simulator = MonteCarloSimulator(seed=42)
    mc_result = simulator.run(result.trades, n_iterations=args.iterations)

    print(f"\n  VaR (95%):        {mc_result.var_95 * 100:.2f}%")
    print(f"  CVaR (95%):       {mc_result.cvar_95 * 100:.2f}%")
    print(f"  Ruin Probability: {mc_result.ruin_probability * 100:.2f}%")
    print(f"  Mean Return:      {mc_result.mean_return * 100:.2f}%")
    print(f"  Median Return:    {mc_result.median_return * 100:.2f}%")
    print(f"  Std Return:       {mc_result.std_return * 100:.2f}%")


# ── Paper Trading CLI ──────────────────────────────────────────────────


async def paper_positions() -> None:
    """List paper trading positions."""
    from src.agents.strategy_exec.brokers.paper import PaperBroker

    broker = PaperBroker()
    positions = await broker.get_positions()

    if not positions:
        print("No open positions")
        return

    print(f"{'Symbol':<8} {'Qty':>6} {'Avg Cost':>10} {'Market':>10} {'Unreal. PnL':>12} {'PnL %':>8}")
    print("-" * 60)
    for p in positions:
        pnl = p.unrealized_pnl or 0.0
        pnl_pct = p.unrealized_pnl_pct or 0.0
        print(f"{p.symbol:<8} {p.quantity:>6} {p.avg_cost:>10.2f} "
              f"{p.market_price or 0.0:>10.2f} {pnl:>12.2f} {pnl_pct:>7.2f}%")


async def paper_orders(status_filter: str | None = None) -> None:
    """List paper trading orders."""
    from src.agents.strategy_exec.brokers.paper import PaperBroker

    broker = PaperBroker()
    orders = await broker.get_orders(status=status_filter)

    if not orders:
        print("No orders found")
        return

    print(f"{'Order ID':<14} {'Symbol':<8} {'Side':<6} {'Type':<8} {'Qty':>6} "
          f"{'Filled':>6} {'Status':<16} {'Created'}")
    print("-" * 90)
    for o in orders:
        print(f"{o.id:<14} {o.symbol:<8} {o.side.value:<6} {o.order_type.value:<8} "
              f"{o.quantity:>6} {o.filled_quantity:>6} {o.status.value:<16} "
              f"{o.created_at.strftime('%Y-%m-%d %H:%M')}")


async def paper_portfolio() -> None:
    """Show paper trading portfolio summary."""
    from src.agents.strategy_exec.brokers.paper import PaperBroker
    from src.services.portfolio_service import PortfolioService

    broker = PaperBroker()
    svc = PortfolioService(broker)

    snapshot = await svc.get_snapshot()
    stats = svc.get_stats()

    print("Paper Trading Portfolio\n")
    print(f"  Cash:         ${snapshot.cash:,.2f}")
    print(f"  Equity:       ${snapshot.equity:,.2f}")
    print(f"  Buying Power: ${snapshot.buying_power:,.2f}")
    print(f"  Total PnL:    ${snapshot.total_pnl:,.2f} ({snapshot.total_pnl_pct:.2f}%)")
    print(f"  Positions:    {len(snapshot.positions)}")

    if stats["total_snapshots"] > 0:
        print(f"\n  Equity Curve Snapshots: {stats['total_snapshots']}")
        print(f"  Total Return:           {stats['total_return_pct']:.2f}%")
        print(f"  Max Drawdown:           {stats['max_drawdown_pct']:.2f}%")
        print(f"  Max Equity:             ${stats['max_equity']:,.2f}")
        print(f"  Min Equity:             ${stats['min_equity']:,.2f}")


async def paper_reset() -> None:
    """Reset paper trading state (orders, positions, cash, equity curve)."""
    from src.agents.strategy_exec.brokers.paper import PaperBroker
    from src.services.portfolio_service import PortfolioService

    broker = PaperBroker()
    svc = PortfolioService(broker)

    broker.reset()
    svc.reset()
    print("Paper trading state reset: orders, positions, cash, and equity curve cleared.")


async def run_sensitivity(args: argparse.Namespace) -> None:
    """Run parameter sensitivity analysis."""
    from datetime import date as dt_date

    from src.backtest.runner import BacktestRunner
    from src.backtest.sensitivity import SensitivityAnalyzer

    start_date = dt_date.fromisoformat(args.from_date)
    end_date = dt_date.fromisoformat(args.to_date)

    # Generate demo data
    import random
    random.seed(42)

    from dataclasses import dataclass
    from datetime import datetime, timedelta

    @dataclass
    class _Bar:
        timestamp: datetime
        open: float
        high: float
        low: float
        close: float
        volume: int

    n_days = (end_date - start_date).days + 1
    price = 100.0 + hash(args.symbol) % 200
    data = []
    for i in range(n_days):
        change = random.uniform(-2, 2)
        price += change
        if price < 1:
            price = 1
        ts = datetime(start_date.year, start_date.month, start_date.day) + timedelta(days=i)
        data.append(_Bar(timestamp=ts, open=price - 0.5, high=price + 1, low=price - 1, close=price, volume=10000))

    start, end, step = args.param_range
    print(f"Running sensitivity analysis for {args.symbol} ({start_date} → {end_date})")
    print(f"  Parameter: {args.param}, Range: [{start}, {end}], Step: {step}")

    def run_with_param(value: float) -> Any:
        config = {"strategy": args.strategy, args.param: value}
        runner = BacktestRunner(args.symbol, start_date, end_date, config)
        return asyncio.get_event_loop().run_until_complete(runner.run(data))

    analyzer = SensitivityAnalyzer()
    result = analyzer.sweep(
        param_name=args.param,
        param_range=(start, end, step),
        run_fn=run_with_param,
    )

    print(f"\n  Data points: {len(result.data_points)}")
    if result.cliffs:
        print(f"  Cliffs detected: {len(result.cliffs)}")
        for cliff in result.cliffs:
            print(f"    - {cliff['param_value']}: {cliff['metric']} dropped {cliff['drop_pct']:.1f}%")
    else:
        print("  No parameter cliffs detected.")

    # Print data table
    print(f"\n  {'Value':>8} {'Sharpe':>8} {'Return':>8} {'Max DD':>8}")
    print("  " + "-" * 38)
    for pt in result.data_points:
        print(f"  {pt['param_value']:>8.1f} {pt['sharpe_ratio']:>8.2f} {pt['total_return']:>7.2f}% {pt['max_drawdown']:>7.2f}%")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aegis-Trader - Multi-Agent quant trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s analyze QQQ SPY              # 分析 QQQ 和 SPY
  %(prog)s analyze --all                # 分析所有核心标的
  %(prog)s analyze --file symbols.txt   # 分析文件中的标的
  %(prog)s list-skills                  # 列出所有技能
  %(prog)s health                       # 检查系统健康状态
  %(prog)s status                       # 显示系统状态
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="运行分析")
    analyze_parser.add_argument(
        "symbols",
        nargs="*",
        help="标的代码 (如 QQQ SPY)，为空时使用 --all 或 --file"
    )
    analyze_parser.add_argument(
        "--all",
        action="store_true",
        help="分析所有核心标的"
    )
    analyze_parser.add_argument(
        "--file",
        type=Path,
        help="从文件读取标的列表 (每行一个)"
    )
    analyze_parser.add_argument(
        "--type",
        choices=["quick", "full", "deep"],
        default="full",
        help="分析类型: quick(快速), full(完整), deep(深度)"
    )
    analyze_parser.add_argument(
        "--format",
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式"
    )
    analyze_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="输出文件路径"
    )

    # list-skills 命令
    subparsers.add_parser("list-skills", help="列出所有可用技能")

    # health 命令
    subparsers.add_parser("health", help="检查系统健康状态")

    # health-check 命令
    health_check_parser = subparsers.add_parser("health-check", help="数据健康自检")
    health_check_parser.add_argument(
        "target",
        choices=["data"],
        help="检查目标: data (数据层健康)",
    )
    health_check_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )

    # status 命令
    subparsers.add_parser("status", help="显示系统状态")

    # reload-config 命令
    subparsers.add_parser("reload-config", help="重新加载配置")

    # version 命令
    subparsers.add_parser("version", help="显示版本信息")

    # api 命令
    api_parser = subparsers.add_parser("api", help="启动 API 服务")
    api_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="绑定地址 (默认: 0.0.0.0)"
    )
    api_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="端口 (默认: 8000)"
    )
    api_parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式自动重载"
    )

    # scheduler 命令
    scheduler_parser = subparsers.add_parser("scheduler", help="调度器管理")
    scheduler_sub = scheduler_parser.add_subparsers(dest="scheduler_action", help="操作")

    scheduler_sub.add_parser("ls", help="列出所有已注册任务")

    pause_parser = scheduler_sub.add_parser("pause", help="暂停指定任务")
    pause_parser.add_argument("job_id", help="任务 ID")

    resume_parser = scheduler_sub.add_parser("resume", help="恢复指定任务")
    resume_parser.add_argument("job_id", help="任务 ID")

    trigger_parser = scheduler_sub.add_parser("trigger", help="手动触发任务")
    trigger_parser.add_argument("job_id", help="任务 ID")

    scheduler_sub.add_parser("history", help="显示最近执行历史")

    # backtest 命令 (with subcommands)
    backtest_parser = subparsers.add_parser("backtest", help="运行回测")
    backtest_sub = backtest_parser.add_subparsers(dest="backtest_action", help="回测子命令")

    # backtest run (default, backward compatible)
    bt_run_parser = backtest_sub.add_parser("run", help="运行标准回测 (默认)")
    bt_run_parser.add_argument(
        "--symbol",
        help="单个标的代码 (如 QQQ)",
    )
    bt_run_parser.add_argument(
        "--symbols",
        nargs="+",
        help="多个标的代码 (如 QQQ SPY NVDA)",
    )
    bt_run_parser.add_argument(
        "--from",
        dest="from_date",
        required=True,
        help="回测起始日期 (YYYY-MM-DD)",
    )
    bt_run_parser.add_argument(
        "--to",
        dest="to_date",
        required=True,
        help="回测结束日期 (YYYY-MM-DD)",
    )
    bt_run_parser.add_argument(
        "--strategy",
        default="pipeline",
        help="策略名称 (默认: pipeline)",
    )
    bt_run_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="报告输出目录 (默认: reports/backtest/)",
    )
    bt_run_parser.add_argument(
        "--no-open",
        action="store_true",
        help="不自动打开 HTML 报告",
    )

    # backtest walk-forward
    bt_wf_parser = backtest_sub.add_parser("walk-forward", help="运行 Walk-Forward 回测")
    bt_wf_parser.add_argument(
        "--symbol",
        required=True,
        help="标的代码 (如 QQQ)",
    )
    bt_wf_parser.add_argument(
        "--from",
        dest="from_date",
        required=True,
        help="回测起始日期 (YYYY-MM-DD)",
    )
    bt_wf_parser.add_argument(
        "--to",
        dest="to_date",
        required=True,
        help="回测结束日期 (YYYY-MM-DD)",
    )
    bt_wf_parser.add_argument(
        "--train-days",
        type=int,
        default=120,
        help="训练窗口天数 (默认: 120)",
    )
    bt_wf_parser.add_argument(
        "--test-days",
        type=int,
        default=20,
        help="测试窗口天数 (默认: 20)",
    )
    bt_wf_parser.add_argument(
        "--step-days",
        type=int,
        default=20,
        help="步进天数 (默认: 20)",
    )
    bt_wf_parser.add_argument(
        "--mode",
        choices=["rolling", "anchored"],
        default="rolling",
        help="Walk-Forward 模式 (默认: rolling)",
    )
    bt_wf_parser.add_argument(
        "--strategy",
        default="pipeline",
        help="策略名称 (默认: pipeline)",
    )
    bt_wf_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="报告输出路径",
    )
    bt_wf_parser.add_argument(
        "--no-open",
        action="store_true",
        help="不自动打开 HTML 报告",
    )

    # backtest mc
    bt_mc_parser = backtest_sub.add_parser("mc", help="运行 Monte Carlo 模拟")
    bt_mc_parser.add_argument(
        "--symbol",
        required=True,
        help="标的代码 (如 QQQ)",
    )
    bt_mc_parser.add_argument(
        "--from",
        dest="from_date",
        required=True,
        help="回测起始日期 (YYYY-MM-DD)",
    )
    bt_mc_parser.add_argument(
        "--to",
        dest="to_date",
        required=True,
        help="回测结束日期 (YYYY-MM-DD)",
    )
    bt_mc_parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="模拟迭代次数 (默认: 1000)",
    )
    bt_mc_parser.add_argument(
        "--strategy",
        default="pipeline",
        help="策略名称 (默认: pipeline)",
    )

    # backtest sensitivity
    bt_sens_parser = backtest_sub.add_parser("sensitivity", help="运行参数敏感性分析")
    bt_sens_parser.add_argument(
        "--symbol",
        required=True,
        help="标的代码 (如 QQQ)",
    )
    bt_sens_parser.add_argument(
        "--from",
        dest="from_date",
        required=True,
        help="回测起始日期 (YYYY-MM-DD)",
    )
    bt_sens_parser.add_argument(
        "--to",
        dest="to_date",
        required=True,
        help="回测结束日期 (YYYY-MM-DD)",
    )
    bt_sens_parser.add_argument(
        "--param",
        required=True,
        help="要分析的参数名 (如 ma_window)",
    )
    bt_sens_parser.add_argument(
        "--range",
        dest="param_range",
        nargs=3,
        type=float,
        required=True,
        metavar=("START", "END", "STEP"),
        help="参数范围 (如 10 50 5)",
    )
    bt_sens_parser.add_argument(
        "--strategy",
        default="pipeline",
        help="策略名称 (默认: pipeline)",
    )

    # paper 命令
    paper_parser = subparsers.add_parser("paper", help="Paper trading (dev/ops tool)")
    paper_sub = paper_parser.add_subparsers(dest="paper_action", help="操作")

    paper_sub.add_parser("positions", help="列出所有持仓")

    orders_parser = paper_sub.add_parser("orders", help="列出所有订单")
    orders_parser.add_argument(
        "--status",
        choices=["pending", "submitted", "filled", "partially_filled", "cancelled", "rejected"],
        help="按状态过滤",
    )

    paper_sub.add_parser("portfolio", help="显示投资组合摘要")

    paper_sub.add_parser("reset", help="重置纸交易状态")

    # llm 命令
    llm_parser = subparsers.add_parser("llm", help="LLM cost governance")
    llm_sub = llm_parser.add_subparsers(dest="llm_action", title="llm commands")

    cost_parser = llm_sub.add_parser("cost", help="Show LLM cost breakdown")
    cost_parser.add_argument("--period", default="7d", choices=["today", "7d", "30d"],
                             help="Time period (default: 7d)")
    cost_parser.add_argument("--group-by", default="agent", choices=["agent", "model", "day"],
                             help="Group by (default: agent)")

    llm_sub.add_parser("budget", help="Show real-time budget status")
    llm_sub.add_parser("cache-stats", help="Show cache hit rate and savings")

    return parser


def parse_args() -> argparse.Namespace:
    """解析命令行参数."""
    return build_parser().parse_args()


def get_symbols_from_args(args: argparse.Namespace) -> list[str]:
    """从参数中获取标的列表."""
    symbols = []

    if args.all:
        config = get_config()
        symbols = config.core_symbols
    elif args.file:
        try:
            with open(args.file) as f:
                symbols = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            sys.exit(1)
    elif args.symbols:
        symbols = args.symbols
    else:
        # 如果没有指定标的，使用默认的核心标的
        config = get_config()
        symbols = config.core_symbols[:3]  # 默认分析前3个

    return symbols


async def _handle_llm_cost(args: argparse.Namespace) -> None:
    """Show LLM cost breakdown."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from src.db import get_session

    now = datetime.now(UTC)
    if args.period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif args.period == "30d":
        since = now - timedelta(days=30)
    else:
        since = now - timedelta(days=7)

    group_by = args.group_by

    async with get_session() as session:
        result = await session.execute(
            text(
                f"SELECT {group_by}, "
                "SUM(input_tokens) as total_input, "
                "SUM(output_tokens) as total_output, "
                "SUM(cost_usd) as total_cost, "
                "COUNT(*) as calls "
                "FROM llm_call_log "
                "WHERE timestamp >= :since AND success = 1 "
                f"GROUP BY {group_by} "
                "ORDER BY total_cost DESC"
            ),
            {"since": since.isoformat()},
        )
        rows = result.fetchall()

    if not rows:
        print(f"No LLM calls found for period: {args.period}")
        return

    total_cost = sum(row[3] for row in rows)
    total_tokens = sum(row[1] + row[2] for row in rows)

    print(f"\nLLM Cost Report ({args.period}, grouped by {group_by})")
    print(f"{'='*80}")
    print(f"Total cost: ${total_cost:.4f}  |  Total tokens: {total_tokens:,}")
    print(f"{'-'*80}")
    print(f"{group_by:<25} {'Input':>10} {'Output':>10} {'Cost':>10} {'Calls':>8}")
    print(f"{'-'*80}")

    for row in rows:
        key, inp, out, cost, calls = row
        print(f"{str(key):<25} {inp:>10,} {out:>10,} ${cost:>9.4f} {calls:>8}")

    print(f"{'-'*80}")
    print(f"{'TOTAL':<25} {sum(r[1] for r in rows):>10,} {sum(r[2] for r in rows):>10,} "
          f"${total_cost:>9.4f} {sum(r[4] for r in rows):>8}")
    print()


async def _handle_llm_budget(args: argparse.Namespace) -> None:
    """Show real-time budget status."""
    from src.llm.budget import get_budget_tracker

    tracker = get_budget_tracker()
    status = await tracker.check()

    print("\nLLM Budget Status")
    print(f"{'='*50}")

    for period in ["daily", "monthly"]:
        info = status[period]
        emoji = "OK" if info["status"] == "ok" else "WARN" if info["status"] == "warning" else "CRIT"
        print(f"  {period.capitalize()}: [{emoji}] {info['status'].upper()}")
        print(f"    Limit:     ${info['limit_usd']:.2f}")
        print(f"    Used:      ${info['used_usd']:.4f}")
        print(f"    Remaining: ${info['remaining_usd']:.4f}")
        print(f"    Usage:     {info['pct']:.1f}%")
        print()

    print()


async def _handle_llm_cache_stats(args: argparse.Namespace) -> None:
    """Show cache hit rate and savings."""
    from src.llm.cache import get_prompt_cache

    cache = get_prompt_cache()
    hit_rate = cache.hit_rate

    print("\nLLM Cache Statistics")
    print(f"{'='*40}")
    print(f"  Hits:      {cache.hits}")
    print(f"  Misses:    {cache.misses}")
    print(f"  Hit Rate:  {hit_rate:.1%}")

    if cache.hits > 0:
        from sqlalchemy import text

        from src.db import get_session

        async with get_session() as session:
            result = await session.execute(
                text("SELECT COALESCE(AVG(cost_usd), 0) FROM llm_call_log WHERE cache_hit = 0")
            )
            avg_cost = result.fetchone()[0]
            estimated_savings = cache.hits * avg_cost
            print(f"  Est. Savings: ${estimated_savings:.4f}")

    print()


async def main_async() -> None:
    """异步主函数."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "analyze":
        symbols = get_symbols_from_args(args)
        if not symbols:
            logger.error("未指定分析标的")
            sys.exit(1)

        await run_analysis(
            symbols=symbols,
            analysis_type=args.type,
            output_format=args.format,
            output_file=args.output
        )

    elif args.command == "list-skills":
        await list_skills()

    elif args.command == "health":
        await check_health()

    elif args.command == "health-check":
        await run_health_check(args)

    elif args.command == "status":
        await show_status()

    elif args.command == "reload-config":
        await reload_config_cmd()

    elif args.command == "version":
        config = get_config()
        print(f"Aegis-Trader v{config.version}")

    elif args.command == "api":
        import uvicorn
        print(f"启动 API 服务: http://{args.host}:{args.port}")
        uvicorn.run(
            "src.api.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )

    elif args.command == "scheduler":
        if not args.scheduler_action:
            print("Usage: aegis scheduler {ls|pause|resume|trigger|history} [args]")
            return
        if args.scheduler_action == "ls":
            await scheduler_ls()
        elif args.scheduler_action == "pause":
            await scheduler_pause(args.job_id)
        elif args.scheduler_action == "resume":
            await scheduler_resume(args.job_id)
        elif args.scheduler_action == "trigger":
            await scheduler_trigger(args.job_id)
        elif args.scheduler_action == "history":
            await scheduler_history()

    elif args.command == "backtest":
        if not args.backtest_action or args.backtest_action == "run":
            await run_backtest(args)
        elif args.backtest_action == "walk-forward":
            await run_walkforward(args)
        elif args.backtest_action == "mc":
            await run_mc(args)
        elif args.backtest_action == "sensitivity":
            await run_sensitivity(args)
        else:
            print(f"Unknown backtest action: {args.backtest_action}")
            sys.exit(1)

    elif args.command == "llm":
        dispatch = {
            "cost": _handle_llm_cost,
            "budget": _handle_llm_budget,
            "cache-stats": _handle_llm_cache_stats,
        }
        handler = dispatch.get(args.llm_action)
        if handler:
            await handler(args)
        else:
            print("Usage: aegis llm {cost|budget|cache-stats} [args]")

    elif args.command == "paper":
        if not args.paper_action:
            print("Usage: aegis paper {positions|orders|portfolio|reset} [args]")
            return
        if args.paper_action == "positions":
            await paper_positions()
        elif args.paper_action == "orders":
            await paper_orders(status_filter=getattr(args, "status", None))
        elif args.paper_action == "portfolio":
            await paper_portfolio()
        elif args.paper_action == "reset":
            await paper_reset()
        else:
            print(f"Unknown paper action: {args.paper_action}")
            sys.exit(1)


def main() -> None:
    """主函数."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

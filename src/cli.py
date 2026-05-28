"""Command-line interface for Aegis-Trader."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

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

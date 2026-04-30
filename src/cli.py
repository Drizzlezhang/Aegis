"""Command-line interface for Aegis-Trader."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.agents.orchestrator import Orchestrator
from src.cli_services import collect_cli_health_report, discover_cli_skills
from src.config import get_config, reload_config
from src.skills.registry import get_global_registry

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_analysis(
    symbols: list[str],
    analysis_type: str = "full",
    output_format: str = "json",
    output_file: Path | None = None
) -> None:
    """运行分析流程."""
    logger.info(f"开始分析 {len(symbols)} 个标的: {symbols}")

    # 获取配置
    config = get_config()

    # 初始化技能注册表
    registry = get_global_registry()
    registry.skill_dirs = config.skill_dirs
    discovered_skills = registry.discover_skills()
    logger.info(f"发现 {len(discovered_skills)} 个技能")

    # 初始化代理编排器
    orchestrator = Orchestrator()

    # 运行分析
    try:
        # 直接调用编排器的 analyze_symbols 方法
        states = await orchestrator.analyze_symbols(symbols)

        # 输出结果
        if output_file:
            with open(output_file, 'w') as f:
                if output_format == "json":
                    import json
                    # 将 AgentState 列表转换为字典列表
                    result_data = [state.dict() for state in states]
                    json.dump(result_data, f, indent=2, default=str)
                else:
                    for state in states:
                        f.write(f"=== Analysis for {state.symbol} ===\n")
                        f.write(str(state))
                        f.write("\n\n")
            logger.info(f"结果已保存到: {output_file}")
        else:
            if output_format == "json":
                import json
                result_data = [state.dict() for state in states]
                print(json.dumps(result_data, indent=2, default=str))
            else:
                for state in states:
                    print(f"=== Analysis for {state.symbol} ===")
                    print(state)
        logger.info(f"分析完成: 处理了 {len(states)} 个标的")

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


def parse_args() -> argparse.Namespace:
    """解析命令行参数."""
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

    return parser.parse_args()


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
    args = parse_args()

    if not args.command:
        # 如果没有命令，显示帮助
        parse_args().parser.print_help()
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

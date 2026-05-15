# Tasks: refactor-phase1-architecture

## Hotfix Waves

### Wave H1（先修 bug）
#### H01: 修复 bull spread 低执行价选择
- 描述: 将 `bull_spread.py` 中低执行价逻辑改为选取满足阈值的最高执行价。
- read_files: [`src/agents/strategy_exec/strategies/bull_spread.py`, `tests/agents/test_strategy*`]
- write_files: [`src/agents/strategy_exec/strategies/bull_spread.py`, `tests/agents/test_strategy*`]
- verify: `python -m pytest tests/agents -q -k bull_spread`
- status: pending

#### H02: 修复 CLI 无子命令崩溃
- 描述: 调整 `src/cli.py` 在无子命令时直接打印 help 并正常退出。
- read_files: [`src/cli.py`, `tests/**`]
- write_files: [`src/cli.py`, `tests/**`]
- verify: `python -m pytest tests -q -k cli`
- status: pending

### Wave H2（设计偏差与代码质量）
#### H03: 清理 strategies package 硬编码导出并补 BaseStrategy
- 描述: 更新 `strategies/__init__.py` 为 lazy compat 导出，仅保留 discovery/base 导出；在 `base.py` 添加 `BaseStrategy` 别名。
- depends_on: [H01]
- read_files: [`src/agents/strategy_exec/strategies/__init__.py`, `src/agents/strategy_exec/strategies/base.py`, `tests/**`]
- write_files: [`src/agents/strategy_exec/strategies/__init__.py`, `src/agents/strategy_exec/strategies/base.py`, `tests/**`]
- verify: `python -m pytest tests -q -k strategy`
- status: pending

#### H04: 修复 state snapshot 深拷贝与 UTC timestamp
- 描述: 更新 `src/models/state.py` 的 timestamp 与 snapshot 复制策略。
- depends_on: [H03]
- read_files: [`src/models/state.py`, `tests/**`]
- write_files: [`src/models/state.py`, `tests/**`]
- verify: `python -m pytest tests -q -k state`
- status: pending

#### H05: 修复 analytics put_call_ratio 序列化安全
- 描述: 将 zero-call-volume 时的 `put_call_ratio` 改为 `None`。
- depends_on: [H04]
- read_files: [`src/models/analytics.py`, `tests/**`]
- write_files: [`src/models/analytics.py`, `tests/**`]
- verify: `python -m pytest tests -q -k analytics`
- status: pending

#### H06: 去除 orchestrator legacy agent 硬编码同步与内联 datetime
- 描述: 删除 `_sync_legacy_agent_refs()` 及其调用，统一时间获取为显式 UTC；若 `report_generator.py` 存在同类反模式同步修复。
- depends_on: [H05]
- read_files: [`src/agents/orchestrator.py`, `src/agents/report_generator.py`, `tests/integration/test_orchestrator.py`, `tests/integration/test_orchestrator_extended.py`]
- write_files: [`src/agents/orchestrator.py`, `src/agents/report_generator.py`, `tests/integration/test_orchestrator.py`, `tests/integration/test_orchestrator_extended.py`]
- verify: `python -m pytest tests/integration/test_orchestrator.py tests/integration/test_orchestrator_extended.py -q`
- status: pending

#### H07: 追加 CLAUDE 并行治理规则
- 描述: 在根 `CLAUDE.md` 末尾追加 4-clone 并行开发治理规则。
- depends_on: [H06]
- read_files: [`CLAUDE.md`, `/Users/bytedance/Downloads/aegis-sprint0-hotfix-prompt.md`]
- write_files: [`CLAUDE.md`]
- verify: `python - <<'PY'
from pathlib import Path
text = Path('CLAUDE.md').read_text()
for token in ['4-Clone 并行开发治理规则', 'Territory Principle', 'Shared File Rules', 'Merge Order']:
    assert token in text
print('ok')
PY`
- status: pending

### Wave H3（全量验证）
#### H08: 执行 hotfix 回归验证并更新 verification
- 描述: 跑 hotfix 相关测试与全量 pytest，更新 `verification.md`。
- depends_on: [H07]
- read_files: [`.specs/refactor-phase1-architecture/requirements.md`, `.specs/refactor-phase1-architecture/verification.md`]
- write_files: [`.specs/refactor-phase1-architecture/verification.md`]
- verify: `python -m pytest tests/ -x -v`
- status: pending

# Change: sprint3-merge-master

## 概述
按 `data-pipeline → analysis-brain → memory-position → frontend-skills` 顺序将 Sprint 3 四个分支合入 `master`，在对应合入点完成 3 个已知 hotfix，并完成合入后验证与交付准备。

## 动机
Sprint 3 已在四个分支分别完成数据、分析、记忆/持仓、前端能力，需要按依赖链进入主线，避免下游分支基于过期主线继续漂移。

## 影响范围
- Git 分支：`master`、`origin/aegis-data`、`origin/aegis-brain`、`origin/aegis-memory`、`origin/aegis-ui`
- 数据层：`src/config.py`、`src/llm/`、`src/agents/data_harvester/`
- 分析层：`src/agents/orchestrator.py`、`src/agents/debate/`、`src/agents/strategy_exec/`、`src/agents/quant_brain/`、`src/models/scoring.py`
- 记忆/持仓层：`src/services/`、`src/agents/position_monitor/`、`src/agents/aegis_memory/`、`src/models/`
- 前端/API 层：`src/api/`、`web/`、`tests/api/`、`tests/e2e/`
- DevKit 状态：`.specs/STATE.md`、`.specs/sprint3-merge-master/`

## 验收目标
- `master` 按指定顺序包含四个 Sprint 3 merge commit。
- data 合入后完成 config profile env override 与 startup health hotfix。
- ui 合入后完成 positions route 使用 `PositionManager.get_all_positions()` 公共 API。
- 每步合入后执行对应 py_compile、关键功能断言、测试命令。
- 最终全量验证通过，已知可忽略失败仅限 `tests/agents/test_vector_store.py` 与 `tests/test_yfinance_skill.py`。
- 推送 `master` 与回同步四个远端分支前必须再次确认，因为这些是对外可见共享状态变更。

## Size: L
## 推断依据
- 范围：跨数据、分析、记忆、API、前端多个模块，并涉及 Git 主线合并。
- 文件数：预计超过 10 个文件，且包含共享文件与冲突处理。
- 风险：影响 `master`、远端分支、测试基线；包含 hotfix 与多轮验证。
- 依赖：严格依赖顺序 `data → brain → memory → ui`，下游依赖上游能力。

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

L 级 gate：`post-spec`、`post-plan`、`pre-ship`、`pre-commit`。对外可见动作（push master、回同步远端分支）单独确认后执行。

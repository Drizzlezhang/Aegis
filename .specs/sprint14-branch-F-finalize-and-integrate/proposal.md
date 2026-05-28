# Change: sprint14-branch-F-finalize-and-integrate

## 概述
Sprint 14 收尾分支：修复 D 分支 review 遗留问题（F1-F4）、交付 C 分支回测验证闭环（F5-F12）、完成多分支合入后的主线集成验证（F13-F14）。

## 动机
- Branch D 合入后 review 发现 4 项轻量改进点（未使用 import、条件评估器扩展、metrics 端点集成测试、规则热加载）
- Branch C 回测验证闭环尚未启动，需完整交付 8 项回测任务
- A/B/D/E 各分支合入后需要主线集成冒烟测试与发布门控
- Sprint 14 需要统一的 release notes、CHANGELOG 与 v0.14.0 tag

## 影响范围
- **Part 1 (D 改进)**: `src/services/alerting.py`, `src/config.py`, `tests/services/test_alerting.py`, `tests/api/test_metrics_route.py`(新), `tests/services/test_alerting_watch.py`(新)
- **Part 2 (C 回测)**: `src/backtest/`(新模块), `src/agents/orchestrator.py`, `src/cli/backtest.py`(新), `src/models/backtest.py`(新), `tests/backtest/`(新), `docs/backtest.md`(新)
- **Part 3 (集成)**: `tests/integration/test_sprint14_smoke.py`(新), `docs/sprint14-release-notes.md`(新), `docs/upgrade-guide.md`(新), `CHANGELOG.md`, `README.md`

## 验收目标
- F1-F4: ruff 0 errors; 新增 ~10 tests 全部 PASS
- F5-F12: `aegis backtest --symbol QQQ --from 2024-01-01 --to 2024-03-31` 成功; 新增 ~22 tests
- F13-F14: 4 集成冒烟场景 PASS; 全量回归 PASS; 性能基线达成; 文档完整
- git tag v0.14.0

## Size: L
## 推断依据
- **范围**: 跨 6 个分支集成（A/B/C/D/E），涉及 3 个 Part、14 项任务
- **关键词**: `finalize`、`integrate`、`backtest`、`release`、`platform`
- **预估文件数**: 30+（新增 ~15 文件，修改 ~10 文件）
- **依赖变更**: 新增 jinja2/plotly 可选依赖；跨分支集成依赖
- **风险**: 需性能基线门控、alembic 多迁移回滚验证、集成冒烟测试

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（完整 L 流程，含 post-spec、post-plan、pre-commit 门控）

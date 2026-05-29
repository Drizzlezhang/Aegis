# Proposal: sprint15-branch-B-backtest-v3-walkforward

## 概述
将 backtest v2 升级到 v3，具备工业级回测能力：walk-forward 框架、成本模型（佣金+滑点）、Position Sizing、出场规则、Monte Carlo、参数敏感性、Benchmark 对比、多 timeframe、持久化与 API。

## Size: L

### 推断依据
| 维度 | 评估 |
|------|------|
| 范围 | 跨系统：backtest + CLI + API + storage + templates |
| 关键词 | feature / redesign / walk-forward / Monte Carlo |
| 预估文件数 | ~20（10-30 区间） |
| 依赖变更 | 内部跨模块（backtest → CLI → API → storage） |
| 风险 | 需回归测试，性能验收门控 |
| project.yaml | scale: L |

### 阶段序列
```
0-CHANGE → 1-SPEC → [post-spec gate] → 2-DESIGN → 3-PLAN → [post-plan gate] → 4-BUILD → 5-VERIFY → [pre-commit gate] → 6-SHIP → [pre-ship gate]
```

## 任务概览（13 tasks × 6 waves）

| Wave | Tasks | 内容 |
|------|-------|------|
| 1 | B1-B3 | CostModel 抽象、Walk-Forward 框架、多 timeframe |
| 2 | B4-B6 | Position Sizers、Exit Rules、Benchmark 对比 |
| 3 | B7-B8 | Monte Carlo、Parameter Sensitivity |
| 4 | B9-B10 | Walk-Forward 报告升级、CLI 升级 |
| 5 | B11-B12 | 回测结果持久化、回测 API 端点 |
| 6 | B13 | Profile + 性能优化 |

## 验收门控
- 1 年日线 walk-forward < 5 min
- 1 年日线单段回测 < 30s
- ~30 新测试 PASS
- CLI 3 个新子命令端到端跑通
- API 4 个新端点 200 + 数据完整
- alembic upgrade/downgrade round-trip OK
- HTML 报告含 ≥5 新章节

## 涉及文件
- 新增: cost_model.py, walk_forward.py, sizers.py, exit_rules.py, monte_carlo.py, sensitivity.py, walkforward_report.html.j2
- 修改: runner.py, storage.py, backtest.py (routes), cli.py
- 迁移: alembic/versions/*_backtest_v3.py
- 测试: 9 个新测试文件

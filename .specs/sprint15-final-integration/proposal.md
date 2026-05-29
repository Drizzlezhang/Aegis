# Change: sprint15-final-integration

## 概述
Sprint 15 最终集成：合入 B(backtest v3) + D(LLM 治理)，开发 C(PaperBroker) + F(Web Dashboard)，完成 Hardening 工程收尾，发布 v0.15.0。

## 动机
Sprint 15 的 B/D 分支已完成开发但未合入 master，C/F 分支尚未开发。需要在一个统一的分支上完成合入、开发、硬化与发版，确保 v0.15.0 达到可发布质量标准（0 fail/0 error、ruff 0、mypy strict 0、coverage ≥75%、CI 强阻断）。

## 影响范围
- **Phase 0**: B/D 合入 master（rebase + 冒烟验证）
- **Phase 1**: Hardening — 测试修复、lint/type 清零、CI 搭建、pre-commit、本地部署冒烟
- **Phase 2**: C 分支 — PaperBroker 完整闭环（broker 抽象 → 撮合 → 订单状态机 → 接线 → Portfolio → API）
- **Phase 3**: F 分支 — Web Dashboard 6 面板（Phase/Backtest/Paper/Alerts/LLMCost/Settings）
- **Phase 4**: 全链路集成测试 + Docker 部署 + v0.15.0 发版
- **涉及模块**: src/agents/、src/services/、src/api/、src/cli.py、web/、tests/、docs/、.github/、Dockerfile、Makefile
- **预估文件数**: 50+

## 验收目标
- `pytest tests/ -n auto` → 0 failed / 0 errors / ≤60s
- `ruff check src/ tests/ web/` → 0 errors
- `mypy src/services` → 0 errors
- coverage ≥ 75%
- CI workflow PR 拦截生效
- PaperBroker 端到端 4 步数据一致
- Web 6 面板可用，Lighthouse ≥80
- 端到端 5 条链路 PASS
- v0.15.0 GitHub Release

## Size: L
## 推断依据
- **范围**: 跨系统（agents/services/api/web/CI/Docker），4 个 Phase，34 个 task
- **关键词**: feature、redesign、migrate、architecture、platform
- **预估文件数**: 50+
- **依赖变更**: B/D 合入 + 新增 PaperBroker/Web Dashboard 模块
- **风险**: 需灰度验证，Phase 1 不达标禁止进 Phase 2

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（全部阶段 + 强制 gate：post-spec、post-plan、pre-commit、pre-ship）

## 前置条件
- B 分支 `sprint15-branch-B-backtest-v3-walkforward` 需存在或可恢复
- D 分支 `sprint15-branch-D-llm-cost-governance` 需存在或可恢复
- 当前 master @ `af07882`

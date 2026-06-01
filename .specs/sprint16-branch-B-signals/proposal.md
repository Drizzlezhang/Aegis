# Change: sprint16-branch-B-signals

## 概述
Sprint16 Branch B：接入 3 个外部信号源（Polymarket + X/Twitter + Macro News），统一通过 Branch A 的 `SignalSource` ABC + `SignalEvent` 契约对外暴露，落库 `signal_events` 表 + 发布 `SignalReceivedEvent` 到 EventBus，替换 mock `/api/signals` 路由为真实查询。

## 动机
Branch A 已产出全部共享契约（数据契约、API 契约、事件契约、DB 契约），但 `/api/signals` 仍返回空 mock。Branch B 负责把真实信号数据接入系统，使后续 C（融合层）、D（推送）、E（前端）分支能基于真实信号数据开发。

## 影响范围
- 新建 `src/signals/` 包（polymarket / x_social / macro_news 三个 adapter）
- 新建 `src/services/signal_collector.py`（SignalCollector 调度器）
- 修改 `src/services/event_bus.py`（新增 `SignalReceivedEvent`）
- 修改 `src/api/routes/signals.py`（替换 mock 为真实查询，移除 `_mock` 字段）
- 新建 `config/x_kols.yaml`（X KOL 列表配置）
- 新建 4 组测试文件（3 adapter 单测 + 1 集成测试）

## 验收目标
1. `pytest tests/signals tests/integration/test_signal_pipeline.py` 全绿
2. `curl /api/signals` 响应里 grep 不到 `_mock`
3. `bash scripts/constitution_grep.sh` 仍然通过
4. 每个 adapter 都实现了 `health_check()` 并返回 bool
5. 提交 8 个 commit：`feat(sprint16-B1)` 到 `feat(sprint16-B6)` + 2 个 chore

## Size: M
## 推断依据
- 范围：跨模块（新包 + 服务 + API + 配置 + 测试），但非跨系统
- 关键词：adapter / collector / signal → "新功能开发"
- 预估文件数：~12
- 依赖：Branch A 契约已就绪，无多系统联调
- 风险：外部 API 依赖（Polymarket Gamma API、Apify/RapidAPI、GDELT/NewsAPI），需 mock 测试
- 项目 scale=L 但本 change 边界清晰（6 feature commit + 2 chore / 2.5 工日），判定 M

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

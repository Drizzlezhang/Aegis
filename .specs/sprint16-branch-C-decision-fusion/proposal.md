# Change: sprint16-branch-C-decision-fusion

## 概述
把 N 条 `SignalEvent` 融合成一个 `FusedSignal`，与 Wyckoff 阶段拼成 `DecisionContext`，落库 + 提供 trace API。

## 动机
Branch A 已提供 contracts（SignalEvent / FusedSignal / DecisionContext）和 decisions 表加列（signal_sources_json / fused_signal_json / context_snapshot_json）。Branch C 在此基础上实现信号融合引擎、决策组装器、持久化与 API 暴露，为后续 D 分支（推送）提供 `DecisionGeneratedEvent`。

## 影响范围
- 新增：`src/services/signal_fusion.py` — SignalFusionEngine
- 新增：`src/services/decision_composer.py` — DecisionComposer
- 修改：`src/services/decision_log.py` — 新增 `append_with_context()` 方法
- 修改：`src/services/event_bus.py` — 新增 `DecisionGeneratedEvent`
- 修改：`src/api/routes/decisions.py` — 替换 mock 路由，新增 `/trace` 端点
- 新增：`tests/services/test_signal_fusion.py`
- 新增：`tests/services/test_decision_composer.py`
- 新增：`tests/integration/test_decision_pipeline.py`

## 验收目标
- [ ] `pytest tests/services/test_signal_fusion.py tests/services/test_decision_composer.py tests/integration/test_decision_pipeline.py` 全绿
- [ ] `curl /api/decisions` 和 `curl /api/decisions/{id}/trace` 响应里无 `_mock`
- [ ] 宪法 grep 通过
- [ ] 提交 7 个 commit：C1~C5 + 2 chore

## Size: M
## 推断依据
- 范围：跨模块（services / API / DB / tests），6-8 文件
- 关键词：feature、engine、composer、integration
- 预估文件数：8
- 依赖变更：仅内部（依赖 Branch A 已合入的 contracts）
- 风险：需回归测试，涉及 DB schema 兼容

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

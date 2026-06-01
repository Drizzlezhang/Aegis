# Requirements: sprint16-branch-C-decision-fusion

## 功能需求

### FR-1: Signal Fusion Engine
- Given: 一组 `SignalEvent`（可能来自不同 source，不同 sentiment）
- When: 调用 `SignalFusionEngine.fuse(signals)`
- Then: 返回 `FusedSignal`，包含：
  - 按 sentiment 计数（bullish_count / bearish_count / neutral_count）
  - 用 confidence 加权的 overall_sentiment
  - fusion_confidence = 主导阵营总权重 / 总权重
  - 冲突检测：bullish_count > 0 且 bearish_count > 0 时 has_conflict=True
  - 冲突轴检测（纯规则，不调 LLM）：
    - 同一 symbol 的 bullish vs bearish → "情绪vs基本面"
    - POLYMARKET vs MACRO_NEWS → "短期vs长期"
    - X_SOCIAL_POST vs MACRO_NEWS → "情绪vs基本面"
    - 默认 → "宏观vs个股"
  - 若 has_conflict=True，调 LLM 生成 conflict_explanation + watch_point（缓存 30min）

### FR-2: Decision Composer
- Given: symbol、wyckoff_phase、current_price、watchlist_position、signals
- When: 调用 `DecisionComposer.compose(...)`
- Then: 返回 `DecisionContext`，包含：
  - 所有输入字段
  - 调用 FR-1 的 fuse 结果作为 fused_signal
  - context_snapshot 包含 phase 置信度、是否 transition 等

### FR-3: 决策落库
- Given: 一个 `DecisionContext` + action + rationale
- When: 调用 `DecisionLog.append_with_context(context, action, rationale)`
- Then:
  - INSERT INTO decisions，填充 signal_sources_json（json.dumps of signal_events）、fused_signal_json、context_snapshot_json
  - 表名 `decisions`（非 `decision_log`）
  - 兼容现有 decisions 表 schema（id, timestamp, symbol, decision_type, data_json, outcome, actual_pnl, reflection, quality_score, quality_tags + 3 个新列）

### FR-4: DecisionGeneratedEvent
- Given: DecisionComposer 完成一次决策
- When: publish `DecisionGeneratedEvent`
- Then: 事件包含 decision_id、symbol、context（DecisionContext），D 分支可订阅

### FR-5: 替换 mock 路由
- Given: decisions 表有数据
- When: `GET /api/decisions`（可选 symbol / limit 参数）
- Then: 返回 `{"items": [...]}`，无 `_mock` 字段
- When: `GET /api/decisions/{decision_id}/trace`
- Then: 返回三段式 trace（signals / fusion / wyckoff+final），无 `_mock` 字段

### FR-6: 集成测试
- Given: 用 `make_fake_signal_event` 造 3 条信号（2 bull + 1 bear）
- When: 运行完整 pipeline（compose → append_with_context → trace API）
- Then: 断言 fused.has_conflict=True、conflict_axis 非空、trace 响应无 `_mock`

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: SignalFusionEngine.fuse() 正确计数并加权 | `pytest tests/services/test_signal_fusion.py` — 单元测试覆盖：全 bullish、全 bearish、混合冲突、空列表 |
| AC-2: 冲突轴检测规则正确 | 同上，参数化测试覆盖 4 种冲突轴场景 |
| AC-3: LLM 解释仅在 has_conflict 时调用，缓存 30min | 同上，mock LLMClient 验证调用次数与缓存行为 |
| AC-4: DecisionComposer.compose() 组装完整 DecisionContext | `pytest tests/services/test_decision_composer.py` — 验证所有字段非空、fused_signal 正确 |
| AC-5: append_with_context() 正确落库 | 同上，使用 :memory: SQLite 验证 INSERT 结果 |
| AC-6: DecisionGeneratedEvent 正确 publish | 同上，mock EventBus 验证 publish 调用 |
| AC-7: GET /api/decisions 返回真实数据，无 _mock | `pytest tests/integration/test_decision_pipeline.py` — HTTP 请求验证 |
| AC-8: GET /api/decisions/{id}/trace 返回三段式，无 _mock | 同上 |
| AC-9: 宪法 grep 通过 | `grep -rn "自动下单\|auto.*order\|place_order" src/ --include="*.py"` 无新增匹配 |

## 用户故事
- As a 交易决策系统，I want 将多条信号融合为一个决策上下文，So that 决策引擎能基于综合信号做出判断
- As a 前端开发者，I want 通过 trace API 查看决策的三段式溯源，So that 用户能理解决策依据

## 非功能需求
### NFR-1: 性能
- SignalFusionEngine.fuse() 纯规则部分 O(n)，n 为信号数（通常 < 20）
- LLM 调用异步非阻塞，超时 10s

### NFR-2: 兼容性
- 不破坏现有 DecisionLog 的 append / query / update_outcome 接口
- decisions 表新列使用 server_default，旧行不受影响

### NFR-3: 可测试性
- SignalFusionEngine 接受可注入的 LLMClient（便于 mock）
- DecisionComposer 接受可注入的 SignalFusionEngine 和 EventBus

## 边界场景
### Edge-1: 空信号列表
- fuse([]) → FusedSignal(overall_sentiment=NEUTRAL, fusion_confidence=0.0, all counts=0, has_conflict=False)

### Edge-2: 单条信号
- fuse([single]) → overall_sentiment = 该信号的 sentiment，fusion_confidence = 该信号的 confidence

### Edge-3: 全部 neutral
- fuse([neutral, neutral]) → overall_sentiment=NEUTRAL, has_conflict=False

### Edge-4: LLM 调用失败
- 若 LLM 超时或报错，conflict_explanation 和 watch_point 保持 None，不阻断融合流程

### Edge-5: decisions 表无新列
- append_with_context 应检测列是否存在，若缺失则降级（不写新列，仅写 data_json）

## 回滚计划
- 若 decisions 表新列写入有问题，可回退到仅写 data_json 的模式
- 新文件（signal_fusion.py / decision_composer.py）可直接删除，不影响现有功能

## 数据/权限影响
- decisions 表新增 3 列写入，不修改现有行
- 无权限变更

## 排除范围（Out of Scope）
- D 分支的推送订阅逻辑（仅提供 DecisionGeneratedEvent）
- 前端 trace 页面（仅提供 API）
- signal_events 表的写入（由 B 分支负责）

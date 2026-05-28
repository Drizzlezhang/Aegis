# Requirements: sprint14-branch-A-phase-quality

## 概述
在 Sprint 13 完成的 7 维 PhasePredictor 基础上，提升 phase 信号质量与可观测性。7 项任务覆盖 ADX 透明化、维度异常事件化、动态权重再分配、i18n、历史持久化、趋势分析、Composite-Score 平滑。

## 功能需求

### FR1 (A1): ADX warm-up 透明化
- `TrendPhaseResult` 新增 `adx_proxy_used: bool = Field(default=False)`
- `_calculate_adx()` 在数据 < 2*period 时回退 `_estimate_adx()` 并将该字段置 True
- `phase_description` 追加 "[ADX proxy mode]" 标记
- **AC1.1**: 30 bar 输入下 `adx_proxy_used=True`，验证方式：单元测试断言
- **AC1.2**: 60 bar 输入下 `adx_proxy_used=False`，验证方式：单元测试断言
- **AC1.3**: proxy 模式下 `phase_description` 包含 "[ADX proxy mode]"，验证方式：单元测试字符串匹配

### FR2 (A2): 维度异常事件化
- 新增 `src/agents/quant_brain/phase_events.py`，定义 `PhaseDimensionFailure` 事件（dataclass: dim_name, error_message, timestamp）
- `_compute_all_dimensions()` 的 except 分支记录事件到 `self._events: list[PhaseDimensionFailure]`
- `TrendPhaseResult` 新增 `degraded_dimensions: list[str] = Field(default_factory=list)`
- 失败维度填充中性值 50 并写入 `result.degraded_dimensions`
- **AC2.1**: mock 某维度抛 RuntimeError，验证 `degraded_dimensions` 包含该维度名，验证方式：单元测试
- **AC2.2**: 失败维度 normalized_score = 50.0，验证方式：单元测试断言
- **AC2.3**: `self._events` 包含对应 `PhaseDimensionFailure` 记录，验证方式：单元测试

### FR3 (A3): 动态权重再分配
- 新增方法 `_rebalance_weights(failed: set[str]) -> dict[str, float]`
- 当 `degraded_dimensions` 非空时，将失败维度权重平均分配到其余维度
- 校验重分配后总权重仍 = 1.0 (±0.001)
- **AC3.1**: 2 个维度失败时，剩余 5 个维度权重均匀增加，验证方式：单元测试
- **AC3.2**: 重分配后总权重 = 1.0 (±0.001)，验证方式：单元测试断言
- **AC3.3**: 无失败维度时返回原始权重，验证方式：单元测试

### FR4 (A4): Phase 解释文本国际化
- 新增 `src/agents/quant_brain/phase_i18n.py`，6 phase × 2 语言 = 12 条短语映射
- `phase_description` 支持 locale 参数（en / zh-CN），默认 en
- `predict()` 接受 `locale: str = "en"` 参数
- **AC4.1**: 同一 phase 在 en 和 zh-CN 下产出不同文本，验证方式：单元测试
- **AC4.2**: 默认 locale=en 时行为不变，验证方式：既有测试全部通过

### FR5 (A5): 历史 phase 持久化
- 新增 `PhaseHistoryRecord` 模型（symbol, timestamp, phase, composite_score, confidence）
- 新增 alembic 迁移创建 `phase_history` 表
- `predict()` 末尾用 `asyncio.create_task` 异步写入历史（不阻塞返回）
- 写入失败仅记录 warning，不抛出
- **AC5.1**: 调用 predict() 5 次后查询表，记录数 = 5，验证方式：集成测试
- **AC5.2**: 写入失败不抛出异常，验证方式：单元测试 mock DB 异常
- **AC5.3**: alembic upgrade head 成功，验证方式：CLI 执行

### FR6 (A6): 短期 phase 趋势分析
- 新增 `_analyze_recent_phases(symbol, lookback=20)` 方法
- 返回 `PhaseTrendSummary`（dominant_phase, transition_count, stability_score）
- `stability_score = 1 - (transition_count / lookback)`
- **AC6.1**: 20 次相同 phase → stability=1.0，验证方式：单元测试
- **AC6.2**: 交替 phase → stability ≈ 0，验证方式：单元测试
- **AC6.3**: dominant_phase 为出现次数最多的 phase，验证方式：单元测试

### FR7 (A7): Composite-Score 平滑
- `PhaseConfig` 新增 `composite_smoothing_alpha: float = Field(default=0.3, ge=0, le=1)`
- `predict()` 输出前对 `composite_score` 做 EMA 平滑（基于上一次结果）
- α=0 时禁用平滑（保持原值）；α=1 时无平滑（等同当前实现）
- **AC7.1**: alpha=0.5 时连续两次差值应被衰减 50%，验证方式：单元测试
- **AC7.2**: alpha=0 时 composite_score 不变，验证方式：单元测试
- **AC7.3**: alpha=1 时 composite_score 等同原始值，验证方式：单元测试

## 非功能需求
- 既有 64 tests 全部 PASS（零回归）
- 新增 ~18 tests，总计 ~82 tests
- `ruff check` 0 errors
- `mypy --strict` 在 phase_predictor.py / phase_events.py / phase_i18n.py 全部通过
- `alembic upgrade head` 成功
- TrendPhaseResult schema 变更向后兼容（所有新字段 Optional / default）
- 不修改 PhaseConfig 现有字段默认值（A7 新增字段除外）

## Out of Scope
- i18n 扩展为 yaml 资源文件（当前仅硬编码字典）
- PhaseHistoryRecord 的查询 API 端点
- PhaseTrendSummary 的实时推送

## 验收标准与验证方式
| AC | 描述 | 验证方式 |
|----|------|---------|
| AC1.1 | 30 bar → adx_proxy_used=True | 单元测试 |
| AC1.2 | 60 bar → adx_proxy_used=False | 单元测试 |
| AC1.3 | proxy 模式 description 含标记 | 单元测试 |
| AC2.1 | 维度异常 → degraded_dimensions 记录 | 单元测试 mock |
| AC2.2 | 失败维度 score=50 | 单元测试 |
| AC2.3 | PhaseDimensionFailure 事件记录 | 单元测试 |
| AC3.1 | 2 维失败 → 5 维权重重分配 | 单元测试 |
| AC3.2 | 重分配后权重和=1.0 | 单元测试 |
| AC3.3 | 无失败时权重不变 | 单元测试 |
| AC4.1 | en/zh-CN 产出不同文本 | 单元测试 |
| AC4.2 | 默认 en 行为不变 | 回归测试 |
| AC5.1 | 5 次 predict → 5 条记录 | 集成测试 |
| AC5.2 | DB 写入失败不抛异常 | 单元测试 mock |
| AC5.3 | alembic upgrade head 成功 | CLI 执行 |
| AC6.1 | 相同 phase → stability=1.0 | 单元测试 |
| AC6.2 | 交替 phase → stability≈0 | 单元测试 |
| AC6.3 | dominant_phase 正确 | 单元测试 |
| AC7.1 | alpha=0.5 衰减 50% | 单元测试 |
| AC7.2 | alpha=0 不变 | 单元测试 |
| AC7.3 | alpha=1 等同原始值 | 单元测试 |

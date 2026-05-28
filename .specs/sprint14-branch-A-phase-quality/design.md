# Design: sprint14-branch-A-phase-quality

## 技术方案概述

在 Sprint 13 硬化的 PhasePredictor 基础上，通过 7 项增强提升信号质量与可观测性。核心思路：**不改变评分算法，只增强输出信号的透明度、鲁棒性和可追溯性**。

## 架构决策 (ADR)

### ADR-1: 事件系统采用轻量 dataclass 而非 EventBus
- **决策**: `PhaseDimensionFailure` 使用 Python `dataclass`，存储在 `PhasePredictor._events` 列表
- **理由**: 维度失败是 PhasePredictor 内部事件，不需要跨模块广播。Sprint 14 Branch D 已实现全局 EventBus，但此处事件仅用于 predict() 调用内的诊断，不需要发布到全局总线
- **替代方案**: 使用 `src/services/event_bus.py` 发布事件 → 拒绝，因为增加了不必要的耦合

### ADR-2: i18n 使用硬编码字典而非 yaml 资源文件
- **决策**: `phase_i18n.py` 使用 Python dict 存储 12 条短语映射
- **理由**: 当前仅 2 种语言 × 6 个 phase = 12 条短语，硬编码字典足够。未来扩展到 5+ 语言时再迁移到 yaml
- **风险**: 扩展性受限，已在 requirements.md out of scope 中标注

### ADR-3: 历史持久化使用 asyncio.create_task 异步写入
- **决策**: `predict()` 末尾用 `asyncio.create_task` 触发 DB 写入，不 await
- **理由**: 避免回测/实时场景被 IO 拖慢。写入失败仅 log warning
- **风险**: 进程崩溃时可能丢失最后一条记录（可接受，phase 历史非关键路径）

### ADR-4: Composite-Score 平滑使用实例级 EMA 状态
- **决策**: `PhasePredictor` 新增 `_smoothed_score: float | None` 实例属性
- **理由**: 每个 PhasePredictor 实例独立维护平滑状态，避免跨 symbol 污染
- **公式**: `smoothed = alpha * raw + (1 - alpha) * prev_smoothed`

## 数据模型变更

### TrendPhaseResult 新增字段
```python
class TrendPhaseResult(BaseModel):
    # ... 既有字段保持不变 ...
    adx_proxy_used: bool = Field(default=False)
    degraded_dimensions: list[str] = Field(default_factory=list)
```

### 新增模型
```python
# src/models/trend_phase.py

class PhaseHistoryRecord(BaseModel):
    """Single phase prediction history entry."""
    id: str | None = None  # UUID, assigned by DB
    symbol: str
    timestamp: datetime
    phase: str  # WyckoffPhase value
    composite_score: float
    confidence: float

class PhaseTrendSummary(BaseModel):
    """Summary of recent phase trend."""
    dominant_phase: str
    transition_count: int
    stability_score: float  # 0-1
```

### PhaseConfig 新增字段
```python
class PhaseConfig(BaseModel):
    # ... 既有字段保持不变 ...
    composite_smoothing_alpha: float = Field(default=0.3, ge=0, le=1)
```

## 模块职责

### phase_events.py (新增)
```
src/agents/quant_brain/phase_events.py
├── PhaseDimensionFailure  # dataclass: dim_name, error_message, timestamp
```
- 纯数据容器，无外部依赖
- 由 `_compute_all_dimensions()` 的 except 分支创建

### phase_i18n.py (新增)
```
src/agents/quant_brain/phase_i18n.py
├── PHASE_DESCRIPTIONS     # dict[WyckoffPhase, dict[str, str]]
├── get_phase_description(phase, locale="en") -> str
```
- 6 phase × 2 locale = 12 条映射
- `get_phase_description()` 为公开 API

### phase_predictor.py (修改)
```
PhasePredictor
├── __init__               # + self._events, self._smoothed_score, self._phase_history_cache
├── predict()              # + locale 参数, + adx_proxy_used, + degraded_dimensions,
│                          #   + weight rebalance, + EMA smoothing, + async history write
├── _compute_all_dimensions()  # + try/except 事件记录
├── _rebalance_weights()   # 新增: 动态权重再分配
├── _analyze_recent_phases()  # 新增: 短期趋势分析
├── _describe_phase()      # 修改: 接受 locale 参数
├── _calculate_adx()       # 修改: 返回 (adx, proxy_used) 或设置实例标志
└── _write_phase_history() # 新增: 异步写入 DB
```

## 数据流

```
predict(ohlcv_data, macro_regime, valuation_range, current_price, locale="en")
  │
  ├─[1] 数据充足性检查 (不变)
  ├─[2] 低波动检查 (不变)
  ├─[3] _compute_all_dimensions()
  │     ├─ 每个维度 try/except
  │     ├─ 失败 → PhaseDimensionFailure 事件 + degraded_dimensions 记录
  │     └─ 成功 → 正常 DimensionScore
  ├─[4] 如果 degraded_dimensions 非空 → _rebalance_weights()
  ├─[5] composite_score 计算
  ├─[6] EMA 平滑 (composite_smoothing_alpha)
  ├─[7] _determine_phase() (不变)
  ├─[8] confidence 计算 (不变)
  ├─[9] phase transition 检测 (不变)
  ├─[10] _describe_phase(locale) → i18n 文本
  ├─[11] asyncio.create_task(_write_phase_history())  # 不阻塞
  └─[12] 返回 TrendPhaseResult
```

## 数据库设计

### phase_history 表
```sql
CREATE TABLE phase_history (
    id UUID PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    phase VARCHAR NOT NULL,
    composite_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_phase_history_symbol_ts ON phase_history(symbol, timestamp);
```

### alembic 迁移
- 新建 `alembic/versions/xxx_add_phase_history.py`
- `down_revision`: 指向当前 HEAD (`4aa2f52baa41`)
- 仅 `upgrade()` 创建表，`downgrade()` 删除表

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| alembic 迁移冲突 | A5 迁移可能与 Branch B 冲突 | 使用独立 revision ID，按时间顺序合并 |
| i18n 扩展性 | 未来多语言需重构 | 当前仅 2 语言，硬编码可接受 |
| EMA 平滑滞后 | 信号响应变慢 | alpha=0.3 为平衡值，alpha=1 可关闭 |
| async 写入丢失 | 进程崩溃丢最后一条 | 非关键路径，可接受 |
| degraded_dimensions 权重再分配 | 剩余维度权重膨胀 | 均匀分配保证总和=1.0 |

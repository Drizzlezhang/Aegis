# Design: sprint13-branch-CD-phase-debate-integration

## 技术方案概述
将 PhasePredictor 的 Wyckoff 相位分析结果桥接到 Debate Agent（多空辩论增强）和 Strategy-Execution Agent（仓位调整），并实现 Cooldown 防抖机制。

核心数据流：
```
PhasePredictor.predict() → state.trend_phase_result (TrendPhaseResult)
    ↓
phase_evidence.generate_phase_evidence() → PhaseEvidence
    ↓
┌───────────────────┬────────────────────────┐
│ Debate Agent      │ Strategy-Exec Agent    │
│ • Bull/Bear 评分  │ • adjust_position_for  │
│ • Judge 权重调整  │   _phase()             │
└───────────────────┴────────────────────────┘
```

## 组件拆分

### C1: PhaseEvidence 数据模型 + 生成器
- 文件: `src/agents/debate/phase_evidence.py` (新建)
- `PhaseEvidence` dataclass: phase, composite_score, confidence, bull_factors, bear_factors, transition_signal, position_bias
- `generate_phase_evidence(result: TrendPhaseResult) -> PhaseEvidence`
- `DIMENSION_DESCRIPTIONS` 常量映射

### C2: Debate Researchers 增强
- 文件: `src/agents/debate/researchers.py` (修改)
- BullResearcher.argue(): 新增 phase evidence 评分因子
- BearResearcher.argue(): 新增 phase evidence 评分因子
- 适配方式: 当前是纯规则引擎（非 LLM），phase evidence 作为额外评分维度直接加减 confidence

### C3: Debate Judge 增强
- 文件: `src/agents/debate/judge.py` (修改)
- 新增 `_calculate_phase_weight_bonus(state)` 方法
- 在 evaluate() 的 delta 计算中应用 bonus

### C4: State 流转验证
- 文件: `src/agents/debate/agent.py` (修改)
- DebateAgent.run() 入口添加 phase 可用性日志

### C5: Strategy Position Sizing
- 文件: `src/agents/strategy_exec/market_context.py` (修改)
- 新增 `adjust_position_for_phase(base_position_size, phase_evidence)` 函数
- 在 StrategyExecAgent.run() 中调用

### C6: Cooldown 逻辑
- 文件: `src/agents/quant_brain/phase_predictor.py` (修改)
- 新增 `_bars_since_last_transition` 计数器
- predict() 中检查 cooldown 再允许 phase 切换

## API 设计

### generate_phase_evidence
```python
def generate_phase_evidence(result: TrendPhaseResult) -> PhaseEvidence:
    """Convert TrendPhaseResult into structured debate evidence."""
```

### adjust_position_for_phase
```python
def adjust_position_for_phase(
    base_position_size: float,
    phase_evidence: PhaseEvidence | None,
) -> float:
    """Adjust position size based on Wyckoff phase signal."""
```

### _calculate_phase_weight_bonus (InvestmentJudge)
```python
def _calculate_phase_weight_bonus(self, state: AgentState) -> dict[str, float]:
    """Calculate bonus weight for bull/bear based on phase confidence."""
```

## 数据模型

### PhaseEvidence (dataclass)
```python
@dataclass
class PhaseEvidence:
    phase: WyckoffPhase
    composite_score: float
    confidence: float
    bull_factors: list[str]
    bear_factors: list[str]
    transition_signal: str | None = None
    position_bias: str = "neutral"  # long|short|neutral|reduce
```

### Phase → Position Bias 映射
| Phase | position_bias |
|-------|--------------|
| accumulation | long |
| markup | long |
| re_accumulation | long |
| distribution | reduce |
| markdown | short |
| re_distribution | reduce |

confidence < 40 → override to "neutral"

### Position Size Multipliers
| position_bias | multiplier | 含义 |
|--------------|-----------|------|
| long | 1.2 | 相位支持入场 |
| reduce | 0.5 | 分发警告 |
| short | 0.3 | 下跌阶段 |
| neutral | 0.8 | 不确定 |

confidence 调制: `adjusted = 1.0 + (multiplier - 1.0) * confidence/100`

### Judge Bonus 计算
```python
confidence_factor = (confidence - 40) / 60  # 0-1, 仅当 confidence >= 40
if composite_score > 60: bull_bonus = confidence_factor * 0.10
elif composite_score < 40: bear_bonus = confidence_factor * 0.10
if transition and direction matches: bonus += 0.05
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Debate 是纯规则引擎，非 LLM prompt 注入 | 需改为评分因子方式 | 将 phase evidence 作为额外 confidence 加减项 |
| Cooldown 与 Branch A transition 检测冲突 | 双重状态管理 | Cooldown 在 transition 检测之前拦截 |
| StrategyExec position sizing 分散 | 集成点不明确 | 在 market_context.py 新增独立函数，agent.py 中调用 |
| 现有测试 confidence 范围变化 (0-1 → 0-100) | 测试断言需更新 | Branch A 已完成迁移，本分支基于最新 master |

## 回滚计划
- PhaseConfig.enabled=False 完全禁用 phase 注入
- 各模块通过 `if state.trend_phase_result` 做 graceful degradation
- 可独立 revert 各模块修改

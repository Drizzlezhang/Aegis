# Design: sprint12-phase-predictor-core

## 技术方案概述
创建 Wyckoff Phase Predictor 5 维引擎，通过加权投票机制识别市场六阶段。引擎作为独立模块接入 QuantBrainAgent 管线，在 macro_regime 之后、LLM report 之前执行。

## 组件拆分

### 1. 数据模型层 (`src/models/trend_phase.py`)
- **WyckoffPhase** (StrEnum): ACCUMULATION / MARKUP / DISTRIBUTION / MARKDOWN / RE_ACCUMULATION / RE_DISTRIBUTION
- **DimensionScore** (BaseModel): 单维度评分容器，含 name/raw_value/normalized_score/weight/weighted_score
- **TrendPhaseResult** (BaseModel): 完整输出，含 phase/confidence/composite_score/dimension_scores/low_volatility_override/phase_description

### 2. 引擎层 (`src/agents/quant_brain/phase_predictor.py`)
- **PhasePredictor**: 主类，含 DEFAULT_WEIGHTS 类变量
  - `predict()`: 异步主入口，编排 5 维度计算 + phase 判定
  - `_score_trend_momentum()`: EMA20/50 交叉 + SMA200 + ADX
  - `_score_volume()`: 相对量 + OBV 方向 + 放量确认
  - `_score_mean_reversion()`: RSI(14) + Bollinger %B
  - `_score_macro()`: MacroRegime 映射 + confidence 调节
  - `_score_valuation()`: PE Band 百分位映射
  - `_determine_phase()`: 综合分 + 量能分 + 趋势方向 → WyckoffPhase
  - 辅助静态方法: `_ema()`, `_calculate_rsi()`, `_calculate_macd()`, `_bollinger_bands()`

### 3. 接线层
- **AgentState** (`src/models/state.py`): 新增 `trend_phase_result: TrendPhaseResult | None = None`
- **QuantBrainAgent** (`src/agents/quant_brain/agent.py`):
  - 新增 `_run_phase_predictor()` 方法
  - `_run_macro_regime()` 末尾保存 regime 到 `state.metadata["macro_regime"]`
  - `run()` 中在 `_run_macro_regime` 之后调用 `_run_phase_predictor`

## 数据模型

### TrendPhaseResult
```
TrendPhaseResult
├── phase: WyckoffPhase          # 判定阶段
├── confidence: float (0-1)      # 置信度
├── composite_score: float (0-100) # 综合得分
├── dimension_scores: list[DimensionScore]  # 5 维度评分
│   ├── [0] trend_momentum (w=0.25)
│   ├── [1] volume (w=0.25)
│   ├── [2] mean_reversion (w=0.20)
│   ├── [3] macro (w=0.15)
│   └── [4] valuation (w=0.15)
├── low_volatility_override: bool  # 低波动覆盖标志
└── phase_description: str         # 人类可读描述
```

### 数据流
```
OHLCV data (list[OHLCV])
  + MacroRegime | None
  + ValuationRange | None
  + current_price | None
        │
        ▼
  PhasePredictor.predict()
        │
        ├─► _score_trend_momentum()  ─┐
        ├─► _score_volume()          ─┤
        ├─► _score_mean_reversion()  ─┼─► composite_score (加权求和)
        ├─► _score_macro()           ─┤
        └─► _score_valuation()       ─┘
                    │
                    ▼
          _determine_phase(composite_score, volume_score, trend_rising)
                    │
                    ▼
            TrendPhaseResult
                    │
                    ▼
          state.trend_phase_result = result
          state.analysis_report += "## Trend Phase (Wyckoff)..."
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 5 维算法评分逻辑错误 | phase 判定不准确 | 每个维度独立单元测试，mock 数据覆盖边界值 |
| Pydantic forward reference 冲突 | AgentState 导入失败 | 文件末尾已有 model_rebuild()，直接导入 TrendPhaseResult 即可 |
| 管线步骤顺序变更 | 现有分析流程受影响 | _run_phase_predictor 包裹 try/except，失败不影响后续步骤 |
| 辅助方法与 agent.py 重复 | 代码冗余 | PhasePredictor 内用 @staticmethod 独立实现，不依赖 agent.py |

## 回滚计划
- 删除 `src/models/trend_phase.py`、`src/agents/quant_brain/phase_predictor.py`
- 恢复 `src/models/__init__.py`、`src/models/state.py`、`src/agents/quant_brain/agent.py`

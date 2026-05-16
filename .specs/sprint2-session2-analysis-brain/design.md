# Design: sprint2-session2-analysis-brain

## 技术方案概述
扩展 Analysis Brain 新增 3 个子系统：左侧/右侧 LEAPS 策略、Anti-whipsaw 决策稳定化、Bull/Bear 辩论系统。同时修复 Sprint 1 `_build_technical_indicators` 空实现。

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| Debate Models | `src/models/debate.py` | DebateArgument/Round/Verdict/Result + InvestmentRating/DebateRole |
| StrategyDecision | `src/models/strategy_decision.py` | DecisionRating + StrategyDecision 结构化输出 |
| LeftSideLeapsStrategy | `src/agents/strategy_exec/strategies/left_side_leaps.py` | 左侧抄底：多因子支撑交汇 + 3 批建仓 |
| RightSideLeapsStrategy | `src/agents/strategy_exec/strategies/right_side_leaps.py` | 右侧跟随：趋势确认 + 一次性建仓 |
| AntiWhipsaw | `src/agents/strategy_exec/anti_whipsaw.py` | 24h 冷却 + JSON 持久化 |
| BullResearcher | `src/agents/debate/researchers.py` | 多头论点生成 |
| BearResearcher | `src/agents/debate/researchers.py` | 空头论点生成 |
| InvestmentJudge | `src/agents/debate/judge.py` | 仲裁规则引擎 |
| DebateAgent | `src/agents/debate/agent.py` | Bull → Bear → Judge pipeline |
| Technical Indicators | `src/agents/quant_brain/agent.py` | 填充 _build_technical_indicators |

## API 设计

### StrategyGenerator 签名（已有，不可改）

```python
def generate(
    self,
    symbol: str,
    options_chain: Any,
    support_levels: list[SupportResistanceLevel],
    resistance_levels: list[SupportResistanceLevel],
    valuation_range: Any | None,
    current_price: float,
    market_context: StrategyMarketContext | None = None,
) -> RecommendedOption | None:
```

### LeftSideLeapsStrategy — 入场条件

```
条件 1: 价格接近支撑 (距离 <3%) — 从 support_levels 取最近支撑
条件 2: valuation_range.is_undervalued == True
条件 3: IV Rank < 50 (从 options_chain 中计算)
条件 4: 技术评分 Grade >= C (从 state.analysis_report 解析)
条件 5: 宏观 Regime != risk_off (从 state.analysis_report 解析)

≥ 3/5 → 生成 LEAPS Call (DTE≥300, delta 0.6-0.8, 3 批 40%+30%+30%)
```

### RightSideLeapsStrategy — 入场条件

```
条件 1: SMA50 > SMA200 (从技术指标判断)
条件 2: RSI 45-65
条件 3: relative_volume > 1.2
条件 4: 宏观 Regime == risk_on 或 neutral

≥ 3/4 → 生成 LEAPS Call (DTE≥300, delta 0.65-0.75, 一次性建仓)
```

### AntiWhipsaw

```python
class AntiWhipsaw:
    def __init__(self, cooldown_hours: int = 24, state_file: str = "~/.aegis-trader/whipsaw_state.json")
    def should_allow(self, symbol: str, new_direction: str) -> tuple[bool, str]
    def record_decision(self, symbol: str, direction: str) -> None
    def clear(self, symbol: str | None = None) -> None
```

状态文件 JSON 格式：`{"AAPL": {"direction": "bullish", "timestamp": "2026-05-15T20:00:00Z"}}`

### Judge 仲裁规则

```
delta = bull.confidence - bear.confidence
delta > 0.3  → STRONG_BUY
delta > 0.1  → BUY
delta > -0.1 → HOLD
delta > -0.3 → SELL
else         → STRONG_SELL

bonus: bull 有 "估值便宜" → +0.1, bear 有 "系统性风险" → -0.15
高质量辩论 (双方 ≥3 key_points) → confidence × 1.1
```

### 技术指标计算

```
close: 最近收盘价
sma50: sum(closes[-50:]) / 50
sma200: sum(closes[-200:]) / 200
rsi: 14-period RSI
macd/macd_signal: EMA12 - EMA26
relative_volume: volumes[-1] / avg(volumes[-20:])
adx: 简化版 (价格波动率 × 3, cap 50)
obv_aligned: price方向 == volume方向
```

## 数据模型

### InvestmentRating (5 级)

```
STRONG_BUY → BUY → HOLD → SELL → STRONG_SELL
```

### DecisionRating (5 级)

```
STRONG_ENTRY → ENTRY → WATCH → REDUCE → EXIT
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 新策略签名不匹配 | discover_strategies 崩溃 | 严格匹配 StrategyGenerator ABC 7 参数签名 |
| Anti-whipsaw 文件损坏 | 启动 crash | JSON load 异常捕获，空 dict 恢复 |
| RSI/MACD 计算偏差 | 评分不准确 | 标注简化版，后续可切换 TA-Lib |
| DebateAgent 未注册 | Orchestrator 不调用 | 当前仅手动调用，合入 main 时注册 |

## 回滚计划
- `rm src/models/debate.py src/models/strategy_decision.py`
- `rm -rf src/agents/debate/`
- `rm src/agents/strategy_exec/strategies/left_side_leaps.py src/agents/strategy_exec/strategies/right_side_leaps.py`
- `rm src/agents/strategy_exec/anti_whipsaw.py`
- `git checkout src/models/__init__.py src/agents/quant_brain/agent.py`
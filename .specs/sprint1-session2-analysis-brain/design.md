# Design: sprint1-session2-analysis-brain

## 技术方案概述
为 QuantBrain 新增两个分析能力模块：100 分制技术评分引擎（纯数值计算）和 5 因子宏观 Regime 判断器。两者不依赖 LLM，通过 Skill 框架和直接模块调用集成到 QuantBrainAgent.run() 流程中。

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| TechnicalScoreBreakdown | `src/models/scoring.py` | 评分数据结构，6 子项加权，total 0-100，grade A-F |
| MacroRegime | `src/models/scoring.py` | Regime 判断结果数据结构 |
| TechnicalScorerSkill | `skills/algorithms/technical_scorer/` | 算法 Skill，接收 OHLCV + 指标，输出评分 |
| MacroRegimeAnalyzer | `src/agents/quant_brain/macro_regime.py` | Regime 多因子判断器，5 因子加权 |
| QuantBrainAgent 扩展 | `src/agents/quant_brain/agent.py` | 集成评分和 Regime 步骤 |

## API 设计

### TechnicalScorerSkill

```python
class TechnicalScorerSkill(BaseSkill):
    skill_type = SkillType.ALGORITHM
    
    async def execute(self, params: dict[str, Any]) -> SkillResult:
        """
        params:
          - ohlcv_data: list[OHLCV]
          - technical_indicators: dict
          - support_levels: list[float]
          - current_price: float
        
        returns: SkillResult(success=True, data=TechnicalScoreBreakdown)
        """
```

遵循现有 skill 规范：`execute(self, params: dict[str, Any]) -> SkillResult`，与 gex_calculator / volume_profile 一致。

### MacroRegimeAnalyzer

```python
class MacroRegimeAnalyzer:
    async def analyze(self, market_data: dict) -> MacroRegime:
        """
        market_data 中可选的 key:
          - VIX: float | None
          - SPY_trend: str (bullish/neutral/bearish)
          - QQQ_trend: str
          - XLK_vs_XLY: float | None (growth/defensive ratio)
          - XLP_vs_XLU: float | None
          - TLT_change_pct: float | None
          - GLD_change_pct: float | None
          - HYG_LQD_ratio_change: float | None
        
        returns: MacroRegime(regime, confidence, factors)
        """
```

### QuantBrain 集成

agent.py 中新增两个步骤处理：

```python
async def _run_technical_score(self, state: AgentState) -> None:
    scorer = self._skill_registry.get_skill("technical_scorer")
    if scorer is None:
        logger.warning("Technical scorer skill not found, skipping")
        return
    
    result = await scorer.execute({
        "ohlcv_data": state.ohlcv_data,
        "technical_indicators": state.technical_indicators,
        "support_levels": [s.price for s in state.support_levels],
        "current_price": current_price,
    })
    
    if result.success:
        score: TechnicalScoreBreakdown = result.data
        state.add_agent_step("technical_score")
        # 将结果追加到 analysis_report，不修改共享 state 模型
        state.analysis_report += (
            f"\n## Technical Score\n"
            f"Grade: {score.grade}, Total: {score.total:.1f}/100\n"
            f"Trend: {score.trend_score}/30 | Deviation: {score.deviation_score}/20 | "
            f"Volume: {score.volume_score}/15 | Support: {score.support_score}/10 | "
            f"MACD: {score.macd_score}/15 | RSI: {score.rsi_score}/10\n"
        )
    else:
        logger.warning(f"Technical scorer failed: {result.error}")

async def _run_macro_regime(self, state: AgentState) -> None:
    analyzer = MacroRegimeAnalyzer()
    market_data = self._build_market_data(state)
    regime = await analyzer.analyze(market_data)
    
    state.add_agent_step("macro_regime")
    state.analysis_report += (
        f"\n## Macro Regime\n"
        f"Regime: {regime.regime} (confidence: {regime.confidence:.2f})\n"
        f"VIX: {regime.vix_signal} | Trend: {regime.market_trend} | "
        f"Sector: {regime.sector_rotation} | Safe Haven: {regime.safe_haven_pressure:.2f}\n"
    )
```

### add_agent_step 数据存储方案（ADR）

`AgentState.add_agent_step` 当前签名为 `(self, agent_name: str)` 仅追加到 `agent_sequence`。该文件为共享文件，不可修改签名。

**决策**: 不修改 `add_agent_step`，不修改 `AgentState`/`QuantResult`。评分和 Regime 结构化数据通过 `state.analysis_report` 文本追加存储。`add_agent_step` 仅用于记录步骤执行顺序。

**替代方案考虑**:
- 方案 A: 修改 `add_agent_step` 签名接受 dict — 被拒绝，state.py 是共享文件禁止修改
- 方案 B: 新增私有字段到 AgentState — 被拒绝，state.py 禁止修改
- 方案 C (采用): analysis_report 文本追加 — 数据可持久化，下游可解析，不改共享文件

## 数据模型

### TechnicalScoreBreakdown

```
trend_score: float      0-30  (SMA50>SMA200=15, Price>SMA50=10, ADX>25=5)
deviation_score: float  0-20  (价格距SMA50偏离度，±2%内满分，±10%外零分)
volume_score: float     0-15  (相对量>1.5=10, OBV方向一致=5)
support_score: float    0-10  (最近支撑<3%=10, 3-5%=5, >5%=0)
macd_score: float       0-15  (MACD>Signal=8, Histogram连续3日扩大=7)
rsi_score: float        0-10  (RSI 30-70=5, 30-45=10, >70=2, <30=3)

total = sum(all_scores)  # 0-100
grade: A(>=80) B(>=65) C(>=50) D(>=35) F(<35)
```

### MacroRegime — 5 因子权重

| 因子 | risk_on 贡献 | risk_off 贡献 | 条件 |
|------|-------------|--------------|------|
| VIX 水位 | +0.3 (<15) | -0.5 (>30) | 15-20: 0, 20-30: -0.3 |
| SPY/QQQ 趋势 | +0.3 (多头) | -0.3 (空头) | 横盘: 0 |
| 板块轮动 | +0.2 (成长) | -0.2 (防御) | 平衡: 0 |
| 避险压力 | +0.1 (TLT/GLD跌) | -0.2 (TLT/GLD涨) | 混合: 0 |
| 信用利差 | +0.1 (改善) | -0.2 (恶化) | 平稳: 0 |

综合得分 > 0.2 → risk_on, < -0.2 → risk_off, 其他 → neutral。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| add_agent_step 签名不足 | 无法存储结构化步骤数据 | 方案 C: analysis_report 文本追加，不改共享文件 |
| 技术指标数据缺失 | 评分引擎收到空 dict | 所有子项默认 0 分，total=0，graceful degradation |
| Skill 加载失败 | QuantBrain 无评分步骤 | warn 日志，跳过步骤，不阻断主流程 |
| 市场 ETF 数据缺失 | Regime 因子无数据 | 缺失因子得分=0，仍产出 neutral regime |
| skill.yaml 格式错误 | SkillRegistry 不可发现 | 严格参照 gex_calculator/volume_profile 格式 |

## 回滚计划
- `rm src/models/scoring.py` + `git checkout src/models/__init__.py` 回退模型层
- `rm -rf skills/algorithms/technical_scorer/` 回退 Skill
- `rm src/agents/quant_brain/macro_regime.py` + `git checkout src/agents/quant_brain/agent.py` 回退 Agent 扩展
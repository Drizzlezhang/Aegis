# Requirements: sprint2-session2-analysis-brain

## 功能需求

### FR-1: 辩论数据模型
- Given: 辩论双方论点、仲裁结果
- When: 辩论系统执行
- Then: 结构化 DebateArgument, DebateRound, JudgeVerdict, DebateResult 模型可用

### FR-2: 左侧/右侧策略区分
- Given: OHLCV + 技术指标 + 估值数据
- When: LeftSideLeapsStrategy / RightSideLeapsStrategy.generate() 调用
- Then: 左侧需满足 ≥3/5 入场条件，右侧需满足 ≥3/4 入场条件

### FR-3: Anti-whipsaw 决策稳定化
- Given: 24h 冷却期内同 symbol 曾有相反方向决策
- When: 新决策方向与上次不同
- Then: should_allow() 返回 False，block 翻转

### FR-4: 结构化决策输出
- Given: 策略执行完成
- When: StrategyDecision 模型实例化
- Then: 包含 5 级评级 + 技术评分 + Regime + 入场因子 + Anti-whipsaw 状态

### FR-5: Bull/Bear 辩论系统
- Given: AgentState 包含分析结果
- When: BullResearcher.argue() / BearResearcher.argue() 调用
- Then: 基于数据生成结构化论点（不调用 LLM）

### FR-6: Judge 仲裁
- Given: Bull + Bear 论点
- When: InvestmentJudge.evaluate() 调用
- Then: 基于 confidence 差值输出 5 级投资评级

### FR-7: DebateAgent 集成
- Given: AgentState 包含分析结果
- When: DebateAgent.run() 调用
- Then: 辩论结果写入 state.analysis_report（不修改 state.py）

### FR-8: 技术指标计算填充
- Given: state.ohlcv_data 至少有 20 条数据
- When: _build_technical_indicators() 调用
- Then: 返回包含 close/sma50/sma200/rsi/macd/relative_volume/adx/obv_aligned 的 dict

### FR-9: 策略自动发现
- Given: strategies/ 目录有 5 个策略文件
- When: discover_strategies() 调用
- Then: 返回 5 个 StrategyGenerator 实例

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: DebateArgument/Round/Verdict/Result 模型可实例化 | 单元测试：构造实例，验证字段类型与默认值 |
| AC-2: LeftSideLeaps 全部 5 条件满足 → 推荐 | 单元测试：模拟多支撑 + undervalued + 低IV + Grade A + risk_on |
| AC-3: LeftSideLeaps <3 条件 → 返回 None | 单元测试：仅 2/5 满足 |
| AC-4: RightSideLeaps SMA50>SMA200+RSI55+放量+risk_on → 推荐 | 单元测试：模拟趋势多头 + momentum 健康 |
| AC-5: Anti-whipsaw 首次决策 → allowed | 单元测试：should_allow('AAPL', 'bullish') → True |
| AC-6: Anti-whipsaw 24h 内翻转 → blocked | 单元测试：record bullish → should_allow bearish → False |
| AC-7: Anti-whipsaw 过期后翻转 → allowed | 单元测试：模拟冷却期过期 |
| AC-8: StrategyDecision 模型实例化 | 单元测试：构造含 DecisionRating + 评分依据 + whipsaw 状态 |
| AC-9: BullResearcher 基于数据生成论点 | 单元测试：高评分+低估 → bull key_points ≥ 2, confidence > 0.5 |
| AC-10: BearResearcher VIX 极端 → high confidence | 单元测试：VIX极端 → confidence > 0.5 |
| AC-11: Judge bull>>bear → STRONG_BUY | 单元测试：bull_confidence=0.9, bear_confidence=0.2 → STRONG_BUY |
| AC-12: Judge 势均力敌 → HOLD | 单元测试：bull △ bear < 0.1 → HOLD |
| AC-13: _build_technical_indicators 返回有效指标 | 单元测试：20+ OHLCV → dict 含 sma50/rsi/macd/relative_volume/adx |
| AC-14: _build_technical_indicators 数据不足返回空 dict | 单元测试：<20 OHLCV → {} |
| AC-15: discover_strategies() 返回 5 个策略 | `python3 -c "assert len(discover_strategies()) == 5"` |
| AC-16: 全量 pytest 通过 | `python -m pytest tests/ -x --tb=short` |

## 用户故事

- As a QuantBrain，我想要从 OHLCV 直接计算技术指标，So that 评分引擎能工作在生产数据上。
- As a StrategyExec，我想要左侧和右侧策略有不同入场逻辑，So that 抄底和跟随场景不被同一规则约束。
- As a StrategyExec，我想要 Anti-whipsaw 防止频繁翻转，So that 不会 24h 内 buy→sell→buy。
- As a Debate Agent，我想要 Bull 和 Bear 双方基于数据生成论点，So that 仲裁结果有依据。

## 非功能需求

### NFR-1: 辩论系统不调用 LLM
BullResearcher, BearResearcher, InvestmentJudge 均为纯规则引擎。

### NFR-2: 技术指标简化实现
不依赖 TA-Lib，足够驱动评分引擎即可。

### NFR-3: Anti-whipsaw JSON 持久化
状态文件 ~/.aegis-trader/whipsaw_state.json，简单可靠。

### NFR-4: 不注册 DebateAgent 到 Orchestrator
等合入 main 时再通过 register_agent() 注册。

## 边界场景

### Edge-1: OHLCV 数据不足 20 条
_build_technical_indicators 返回空 dict，评分引擎所有因子得分为 0。

### Edge-2: Anti-whipsaw 状态文件损坏
_load_state 捕获异常，用空 dict 恢复，不崩溃。

### Edge-3: 策略 generate() 参数缺失
market_context=None → 使用默认值，不崩溃。

### Edge-4: 辩论双方 confidence 完全相等
Judge 返回 HOLD。

## 回滚计划
- 新建文件 `rm` 删除
- `__init__.py` + `agent.py` 修改 `git checkout` 恢复

## 数据/权限影响
- Anti-whipsaw 写 `~/.aegis-trader/whipsaw_state.json`
- 无数据库/API/环境变量变更
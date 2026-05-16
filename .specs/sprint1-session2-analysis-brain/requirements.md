# Requirements: sprint1-session2-analysis-brain

## 功能需求

### FR-1: 技术评分数据模型
- Given: 6 个评分细项（trend/deviations/volume/support/macd/rsi）各有数值
- When: TechnicalScoreBreakdown 实例化
- Then: `total` 返回 0-100 的加权总分，`grade` 返回 A(>=80)/B(>=65)/C(>=50)/D(>=35)/F(<35)

### FR-2: 宏观 Regime 数据模型
- Given: regime 类型、confidence、各因子信号
- When: MacroRegime 实例化
- Then: 返回结构化 regime 判断结果，支持 `risk_on`/`risk_off`/`neutral`

### FR-3: 100 分制技术评分引擎
- Given: OHLCV 数据、技术指标、支撑位、当前价格
- When: TechnicalScorerSkill.execute() 被调用
- Then: 返回 TechnicalScoreBreakdown，各子项分数在定义范围内，总分 0-100

### FR-4: 宏观 Regime 多因子判断
- Given: 市场 ETF 数据（VIX/SPY/QQQ/XLK/XLY/XLU/TLT/GLD/HYG/LQD）
- When: MacroRegimeAnalyzer.analyze() 被调用
- Then: 返回风险偏好评级，缺失数据因子得分为 0（graceful degradation）

### FR-5: QuantBrain ANALYSIS_STEPS 扩展
- Given: TechnicalScorerSkill 和 MacroRegimeAnalyzer 已可用
- When: QuantBrainAgent.run() 执行分析
- Then: 分析流程包含 technical_score 和 macro_regime 步骤，结果写入 state

### FR-6: 模型导出
- Given: scoring.py 包含 TechnicalScoreBreakdown 和 MacroRegime
- When: 从 src.models 导入
- Then: 两个模型可通过 `from src.models import TechnicalScoreBreakdown, MacroRegime` 获取

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: TechnicalScoreBreakdown.total 正确计算 6 项加权和 | 单元测试：构造满分 (30+20+15+10+15+10=100) 和零分实例，断言 total |
| AC-2: TechnicalScoreBreakdown.grade 按阈值输出 A/B/C/D/F | 单元测试：total=100→A, total=80→A, total=65→B, total=50→C, total=35→D, total=0→F |
| AC-3: TechnicalScorerSkill 趋势满分场景正确评分 | 单元测试：SMA50>SMA200, Price>SMA50, ADX>25 → trend_score=30 |
| AC-4: TechnicalScorerSkill 乖离率 0% 满分场景 | 单元测试：价格距 SMA50=0 → deviation_score=20 |
| AC-5: TechnicalScorerSkill 超卖反弹 RSI 场景 | 单元测试：RSI=35 (30-45) → rsi_score=10 |
| AC-6: TechnicalScorerSkill 全零/全满分场景 | 单元测试：全零 → total=0, grade=F; 全满分 → total=100, grade=A |
| AC-7: MacroRegimeAnalyzer VIX<15 + 多头 → risk_on | 单元测试：模拟 VIX=12, SPY 多头排列 → regime=risk_on |
| AC-8: MacroRegimeAnalyzer VIX>30 + 避险 → risk_off | 单元测试：模拟 VIX=35, TLT/GLD 上涨 → regime=risk_off |
| AC-9: MacroRegimeAnalyzer 全中性 → neutral | 单元测试：所有因子得分 0 → regime=neutral |
| AC-10: MacroRegimeAnalyzer 数据缺失不崩溃 | 单元测试：空 market_data → 不抛异常，regime 正常返回 |
| AC-11: 评分引擎通过 state.add_agent_step 写入结果 | 集成测试：run() 后 state.agent_sequence 包含 technical_score 相关记录 |
| AC-12: 全量 pytest 通过 | `python -m pytest tests/ -x --tb=short` 0 失败 |
| AC-13: 模型可从 src.models 导入 | `python3 -c "from src.models import TechnicalScoreBreakdown, MacroRegime"` 成功 |
| AC-14: Skill 可被 SkillRegistry 发现 | `python3 -c "from src.skills import get_global_registry; r=get_global_registry(); print(r.get_skill('technical_scorer'))"` 非 None |

## 用户故事

- As a QuantBrain，我想要将 100 分制技术评分加入分析流程，So that 我可以量化每个标的的技术面强度。
- As a QuantBrain，我想要在分析时判断宏观 Regime，So that 策略生成可以根据 risk_on/risk_off 调整仓位和策略类型。
- As a StrategyExec，我想要读取 state 中的 technical_score 和 macro_regime，So that 策略生成可以利用这些信号。

## 非功能需求

### NFR-1: 评分引擎不依赖 LLM
TechnicalScorerSkill 为纯数值计算，不调用 LLM 或外部 API。

### NFR-2: Graceful Degradation
MacroRegimeAnalyzer 在数据不完整时不崩溃，缺失因子得分为 0，仍产出 regime 判断。

### NFR-3: Skill YAML 合规
TechnicalScorerSkill 必须有 `skill.yaml`，格式与 volume_profile/gex_calculator 一致，否则 SkillRegistry 不可发现。

### NFR-4: 共享文件只追加
`src/models/__init__.py` 只在末尾追加 import，不改动已有导出。`src/agents/__init__.py` 如有必要同样只追加。

## 边界场景

### Edge-1: 技术指标数据缺失
评分引擎收到空 dict → 所有子项得分为 0，total=0，grade=F。

### Edge-2: 极端乖离率
价格距 SMA50 > ±10% → deviation_score=0，不出现负分。

### Edge-3: RSI 边界值
RSI=30 恰好 → 按 30-45 区间处理为 10 分（超卖反弹）。RSI=70 恰好 → 按 >70 处理为 2 分。

### Edge-4: 支撑位列表为空
无支撑位时 support_score=0。

### Edge-5: QuantBrain run() 中 skill 加载失败
TechnicalScorerSkill 加载失败 — warn 日志，跳过评分，不阻断主流程。

## 回滚计划
- 新建文件可直接 `rm` 删除
- `__init__.py` 追加行可 `git revert`
- 评分引擎和 macro regime 不依赖 LLM，回滚无数据影响

## 数据/权限影响
- 无新增外部依赖
- 不读写数据库
- 不修改环境变量
- 纯内存计算
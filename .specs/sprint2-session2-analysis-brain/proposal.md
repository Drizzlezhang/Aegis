# Change: sprint2-session2-analysis-brain

## 概述
Sprint 2 Session 2：左侧/右侧策略区分、Anti-whipsaw 决策稳定化、Bull/Bear 辩论系统、技术指标计算填充。

## 动机
- Sprint 1 的 100 分制评分引擎缺少实际技术指标输入（`_build_technical_indicators` 返回空 dict）
- 需要区分左侧抄底和右侧跟随策略，提供不同建仓逻辑
- 需要防止短期内决策翻转（Anti-whipsaw）
- 需要结构化辩论系统在多空观点中仲裁

## 影响范围
- 新建：`src/models/debate.py` — 辩论数据模型
- 新建：`src/models/strategy_decision.py` — 结构化决策输出
- 新建：`src/agents/strategy_exec/strategies/left_side_leaps.py`
- 新建：`src/agents/strategy_exec/strategies/right_side_leaps.py`
- 新建：`src/agents/strategy_exec/anti_whipsaw.py`
- 新建：`src/agents/debate/` — agent.py, researchers.py, judge.py, __init__.py
- 修改：`src/agents/quant_brain/agent.py` — 填充 _build_technical_indicators
- 修改：`src/models/__init__.py` — 末尾追加导出
- 新建：4 个测试文件

## 验收目标
1. 左侧/右侧策略自动发现（5 个策略，Sprint 1 的 3 + Sprint 2 的 2）
2. Anti-whipsaw 24h 冷却，同 symbol 不翻转方向
3. Bull/Bear/Judge 辩论 pipeline 输出结构化仲裁
4. 技术指标计算返回有效的 RSI/SMA/MACD/volume
5. 全量 pytest 通过

## Size: M
## 推断依据
- 范围：跨模块（models + agents/debate + strategy_exec + quant_brain），影响 4 个目录
- 预估文件数：~14 文件（新建 12 + 修改 2）
- 依赖变更：仅内部，不新增外部依赖
- 风险：策略签名兼容性、技术指标计算正确性、辩论系统不调用 LLM
- 特征：new feature with new agent (debate), strategy extension, and fix

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
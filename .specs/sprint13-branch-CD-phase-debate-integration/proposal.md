# Change: sprint13-branch-CD-phase-debate-integration

## 概述
将 PhasePredictor 的 Wyckoff 相位分析结果桥接到 Debate Agent 和 Strategy-Execution Agent，实现相位感知的辩论增强和仓位调整。

## 动机
PhasePredictor 已产出 TrendPhaseResult（含 phase、composite_score、confidence、transition），但下游 Debate 和 Strategy-Execution 尚未消费这些信号。需要建立数据桥接，让相位分析结果影响多空辩论和仓位决策。

## 影响范围
### 新增文件
- `src/agents/debate/phase_evidence.py` — PhaseEvidence 数据模型 + generate_phase_evidence()
- `tests/integration/test_phase_debate_pipeline.py` — Phase→Debate 集成测试
- `tests/integration/test_phase_transition.py` — Phase 转换场景测试
- `tests/integration/test_config_sensitivity.py` — 配置敏感度测试
- `tests/integration/test_position_phase.py` — 仓位调整测试

### 修改文件
- `src/agents/debate/researchers.py` — Bull/Bear Researcher 注入 phase evidence
- `src/agents/debate/judge.py` — Judge 增加 phase weight bonus
- `src/agents/debate/agent.py` — DebateAgent 入口日志
- `src/agents/strategy_exec/market_context.py` — 新增 adjust_position_for_phase()
- `src/agents/quant_brain/phase_predictor.py` — Cooldown 逻辑

## 验收目标
1. 所有测试 PASS, 0 failures
2. Phase evidence 正确注入 Debate context
3. Judge 权重调整逻辑正确
4. Strategy position sizing 正确响应 phase bias
5. Cooldown 机制防止信号抖动
6. 无 phase data 时所有模块 graceful degradation
7. ruff check + mypy 零错误

## Size: M
## 推断依据
- 范围：跨 3 个模块（debate + strategy_exec + quant_brain）
- 预估文件数：5 新增 + 5 修改 = ~10 文件
- 依赖变更：新增内部模块依赖，无外部依赖
- 风险：需回归测试，涉及 pipeline 数据流

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

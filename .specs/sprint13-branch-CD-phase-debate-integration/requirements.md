# Requirements: sprint13-branch-CD-phase-debate-integration

## 功能需求

### FR-1: Phase Evidence 生成器 (C1)
- Given: TrendPhaseResult 包含 phase、composite_score、dimension_scores、confidence、transition
- When: 调用 generate_phase_evidence(result)
- Then: 返回 PhaseEvidence，包含 bull_factors（score>60 的维度）、bear_factors（score<40 的维度）、position_bias（按 phase 映射）、transition_signal

### FR-2: Phase → Position Bias 映射 (C1)
- Given: WyckoffPhase 值
- When: 映射到 position_bias
- Then: accumulation/re_accumulation→"long", markup→"long", distribution/re_distribution→"reduce", markdown→"short"
- When: confidence < 40
- Then: position_bias override to "neutral"

### FR-3: Bull/Bear Factors 生成 (C1)
- Given: dimension_scores dict
- When: score > 60 → 生成 bull_factor（维度中文名 + 得分 + 描述）
- When: score < 40 → 生成 bear_factor
- Then: 使用 DIMENSION_DESCRIPTIONS 映射维度名到中文

### FR-4: Bull Researcher Phase 注入 (C2)
- Given: state.trend_phase_result 存在
- When: BullResearcher.argue() 构建 prompt
- Then: 注入 phase_context（phase、composite_score、confidence、position_bias、bull_factors、transition）
- Given: state.trend_phase_result 为 None
- Then: 不注入任何 phase 内容（graceful degradation）

### FR-5: Bear Researcher Phase 注入 (C2)
- Given: state.trend_phase_result 存在
- When: BearResearcher.argue() 构建 prompt
- Then: 注入 phase_context，重点展示 bear_factors

### FR-6: Judge Phase Weight Bonus (C3)
- Given: state.trend_phase_result 存在且 confidence >= 40
- When: composite_score > 60 → bull_bonus = confidence_factor * 0.10
- When: composite_score < 40 → bear_bonus = confidence_factor * 0.10
- When: 有 transition 且方向一致 → 额外 +5%
- Given: confidence < 40 或无 phase data
- Then: bonus = 0

### FR-7: State 流转验证 (C4)
- Given: Orchestrator pipeline 顺序为 Quant-Brain → Debate
- When: DebateAgent.run() 入口
- Then: 日志记录 phase evidence 可用性

### FR-8: Strategy Position Sizing (C5)
- Given: PhaseEvidence 和 base_position_size
- When: position_bias="long" → multiplier=1.2
- When: position_bias="reduce" → multiplier=0.5
- When: position_bias="short" → multiplier=0.3
- When: position_bias="neutral" → multiplier=0.8
- Then: adjusted = base * (1 + (multiplier-1) * confidence/100)
- Given: phase_evidence=None → 返回 base_position_size

### FR-9: Cooldown 逻辑 (C6)
- Given: PhasePredictor 实例
- When: 连续调用 predict()，phase 发生变化
- Then: 仅当 _bars_since_last_transition >= phase_transition_cooldown_bars 时允许切换
- When: cooldown 内 → 保持 _last_phase，transition=None

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: generate_phase_evidence 正确映射 phase→position_bias | 单元测试：6 种 phase 各验证 bias |
| AC-2: confidence<40 时 position_bias="neutral" | 单元测试：confidence=30 → neutral |
| AC-3: dimension_scores 正确生成 bull/bear factors | 单元测试：score>60 生成 bull，score<40 生成 bear |
| AC-4: Bull Researcher 注入 phase context | 集成测试：mock state with phase，验证 prompt 包含 phase 信息 |
| AC-5: Bear Researcher 注入 phase context | 集成测试：mock state with phase，验证 prompt 包含 bear_factors |
| AC-6: 无 phase data 时 graceful degradation | 集成测试：state.trend_phase_result=None，验证正常运行 |
| AC-7: Judge bonus 仅在 confidence>=40 时生效 | 集成测试：confidence=30 → bonus=0 |
| AC-8: Judge bonus 方向正确 | 集成测试：bullish score → bull_bonus>0, bear_bonus=0 |
| AC-9: adjust_position_for_phase 正确计算 | 单元测试：5 种 bias × 不同 confidence |
| AC-10: Cooldown 阻止频繁切换 | 集成测试：cooldown_bars=3，连续 2 次变化不触发 transition |
| AC-11: Cooldown 过期后允许切换 | 集成测试：超过 cooldown_bars 后正常检测 transition |
| AC-12: ruff check + mypy 零错误 | CLI 运行 ruff + mypy |
| AC-13: 全量回归测试通过 | pytest tests/ -x --tb=short |

## 用户故事
- As a Debate Agent, I want phase evidence injected into my context, So that I can make more informed bull/bear arguments
- As a Strategy Agent, I want position sizing adjusted by Wyckoff phase, So that I reduce exposure in distribution/markdown phases
- As a system operator, I want cooldown to prevent whipsaw signals, So that phase transitions are stable and reliable

## 非功能需求

### NFR-1: Graceful Degradation
- 所有新增模块在 state.trend_phase_result=None 时必须正常运行，不抛异常

### NFR-2: 代码质量
- ruff check src/ → 0 errors
- mypy src/agents/debate/phase_evidence.py --strict → 0 errors

### NFR-3: 测试覆盖
- phase_evidence.py > 95% 覆盖率
- 所有集成测试不依赖外部网络/API

## 边界场景

### Edge-1: 空 dimension_scores
- Given: dimension_scores 为空 list
- Then: bull_factors 和 bear_factors 均为空

### Edge-2: 所有维度得分在 40-60 之间
- Given: 所有 dimension score 在 [40, 60]
- Then: bull_factors 和 bear_factors 均为空，position_bias 按 phase 正常映射

### Edge-3: confidence 恰好等于 40
- Given: confidence = 40
- Then: position_bias 不 override（>= 40 视为可信），Judge bonus = 0（confidence_factor = 0）

### Edge-4: Cooldown 边界
- Given: cooldown_bars=3, _bars_since_last_transition=2
- Then: phase 切换被阻止
- Given: _bars_since_last_transition=3
- Then: phase 切换被允许

## 回滚计划
- 所有新增代码通过 feature flag（PhaseConfig.enabled）控制
- 设置 enabled=False 即可完全禁用 phase 注入
- 各模块通过 `if state.trend_phase_result` 做 graceful degradation

## 数据/权限影响
- 无数据库 schema 变更
- 无新增外部依赖
- 无权限变更

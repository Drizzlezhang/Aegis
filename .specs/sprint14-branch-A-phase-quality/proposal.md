# Change: sprint14-branch-A-phase-quality

## 概述
在 Sprint 13 完成的 7 维 PhasePredictor 基础上，提升 phase 信号质量与可观测性。7 项任务覆盖：ADX warm-up 透明化、维度异常事件化、动态权重再分配、Phase 解释文本国际化、历史 phase 持久化、短期 phase 趋势分析、Composite-Score 平滑。

## 动机
Sprint 13 硬化了 PhasePredictor 的核心算法，但信号质量与可观测性仍有提升空间：
- ADX 回退 proxy 时无感知
- 维度计算失败静默吞掉
- 权重固定无法适应降级场景
- phase 描述仅英文
- 无历史 phase 记录与趋势分析
- composite_score 无平滑导致信号抖动

## 影响范围
- `src/agents/quant_brain/phase_predictor.py` — A1/A2/A3/A7 修改
- `src/agents/quant_brain/phase_events.py` — A2 新增
- `src/agents/quant_brain/phase_i18n.py` — A4 新增
- `src/models/trend_phase.py` — A1/A2/A6 新增字段
- `src/services/database.py` — A5 新增表
- `src/config.py` — A7 新增 composite_smoothing_alpha
- `alembic/versions/` — A5 新增迁移
- `tests/agents/test_phase_predictor.py` — 扩展
- `tests/agents/test_phase_events.py` — A2 新增
- `tests/agents/test_phase_i18n.py` — A4 新增

## 验收目标
1. 既有 64 tests 全部 PASS（零回归）
2. 新增 ~18 tests，总计 ~82 tests
3. ruff check 0 errors
4. mypy --strict 在 phase_predictor.py / phase_events.py / phase_i18n.py 全部通过
5. alembic upgrade head 成功
6. TrendPhaseResult schema 变更向后兼容

## Size: M
## 推断依据
- 7 个任务，跨 3 个新文件 + 5 个修改文件 + alembic 迁移
- 新增模块（phase_events、phase_i18n）+ 数据库表
- 涉及 Pydantic schema 变更、数据库迁移、i18n 架构
- 预估 ~10 文件变更，~18 新测试
- 风险：alembic 迁移需协调，schema 变更需向后兼容

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

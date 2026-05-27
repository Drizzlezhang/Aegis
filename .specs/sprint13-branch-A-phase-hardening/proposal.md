# Change: sprint13-branch-A-phase-hardening

## 概述
PhasePredictor 硬化：8 项任务覆盖参数化、算法替换、性能优化、新字段和测试补全。

## 动机
Sprint 12 完成后 PhasePredictor 已具备 7 维引擎，但存在硬编码敏感度参数、简化 ADX proxy、RSI 全量计算 O(n²) 等问题。本分支系统性硬化：
- A1: Velocity/Acceleration 敏感度参数化
- A2: RSI 增量计算优化
- A3: 标准 Wilder ADX 替换简化 proxy
- A4: Valuation 维度测试补全
- A5: _determine_phase 边界组合测试
- A6: 测试 Native Async 迁移
- A7: confidence 输出字段
- A8: phase_transition_signal

## 影响范围
- `src/agents/quant_brain/phase_predictor.py` — A1/A2/A3/A7/A8 修改
- `src/models/trend_phase.py` — A7/A8 新增字段
- `tests/agents/test_phase_predictor.py` — A4/A5/A7/A8 新增测试 + A6 async 迁移
- `tests/integration/test_phase_predictor_pipeline.py` — A6 async 迁移
- `tests/conftest.py` — A6 async fixture 适配
- `pyproject.toml` — A6 asyncio_mode 配置

## 验收目标
1. 既有 29 tests 全部 PASS（无回归）
2. 新增约 15 条测试，总计约 44 tests
3. `ruff check` 0 errors
4. `mypy --strict` 0 errors
5. 所有新方法有 docstring + type annotations

## Size: S
## 推断依据
- 8 个任务但全部集中在 PhasePredictor 单文件 + 模型 + 测试
- 无架构变更、无新模块、无外部依赖
- 约 200-300 行新增/修改代码
- 执行顺序: A6 → A3 → A2 → A1 → A7 → A8 → A4+A5

## 阶段序列
0 → 1 → 4 → 5 → 6

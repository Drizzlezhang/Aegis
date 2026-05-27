# Tasks: sprint12-branch-d-tests

## Wave 1: conftest.py Fixtures
- [ ] 1.1 创建 `tests/conftest.py`（如不存在）或追加 6 个 mock OHLCV fixtures
  - `mock_ohlcv_linear_up`: 60 根线性上涨
  - `mock_ohlcv_exponential_up`: 60 根指数上涨
  - `mock_ohlcv_linear_down`: 60 根线性下跌
  - `mock_ohlcv_flat`: 60 根极低波动
  - `mock_ohlcv_volatile`: 60 根高波动正弦
  - `mock_ohlcv_short`: 10 根数据不足

## Wave 2: 单元测试
- [ ] 2.1 创建 `tests/agents/test_phase_predictor.py` (29 tests)
  - 基础运行 (3): 返回类型、7 维、权重和
  - 维度评分 (9): trend_momentum×2, volume, mean_reversion, macro, velocity×2, acceleration×2
  - Phase 判定 (6): 全部 6 种 Wyckoff phase
  - 低波动过滤 (2): 触发/不触发
  - Config 覆盖 (3): 权重/阈值/disabled
  - 数据不足 (2): 短数据/空数据
  - 边界值 (1): score clipping

## Wave 3: 集成测试
- [ ] 3.1 创建 `tests/integration/test_phase_predictor_pipeline.py` (3 tests)
  - standalone pipeline integration
  - report append
  - macro regime integration

## Wave 4: 验证
- [ ] 4.1 运行 `pytest tests/agents/test_phase_predictor.py tests/integration/test_phase_predictor_pipeline.py -v --tb=short`
- [ ] 4.2 运行 `pytest tests/ -x --tb=short -q` 确保无回归

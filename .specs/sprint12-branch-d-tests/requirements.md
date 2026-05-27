# Requirements: sprint12-branch-d-tests

## 概述
为 PhasePredictor 7 维引擎创建完整测试套件，覆盖单元测试、维度测试、边界测试和集成测试。

## 功能需求

### FR1: conftest.py 测试 Fixtures
- 创建 `tests/conftest.py`（如不存在）或追加 fixtures
- 提供 6 个 mock OHLCV fixtures:
  - `mock_ohlcv_linear_up`: 60 根线性上涨 (100→110)
  - `mock_ohlcv_exponential_up`: 60 根指数上涨 (加速)
  - `mock_ohlcv_linear_down`: 60 根线性下跌 (110→100)
  - `mock_ohlcv_flat`: 60 根极低波动
  - `mock_ohlcv_volatile`: 60 根高波动正弦
  - `mock_ohlcv_short`: 10 根数据不足

### FR2: test_phase_predictor.py 单元测试 (29 tests)
- **基础运行 (3)**: 返回类型验证、7 维验证、权重和=1.0
- **维度测试 (9)**: trend_momentum 涨/跌、volume 范围、mean_reversion 中性、macro=None、velocity 涨/跌、acceleration 线性/指数
- **Phase 判定 (6)**: Markup/Markdown/Re-Accumulation/Re-Distribution/Accumulation/Distribution
- **低波动过滤 (2)**: 触发/不触发
- **Config 覆盖 (3)**: 自定义权重/阈值/disabled
- **数据不足 (2)**: 短数据/空数据
- **边界值 (1)**: score clipping [0,100]
- **集成 (3)**: standalone pipeline、report append、macro regime

### FR3: test_phase_predictor_pipeline.py 集成测试 (3 tests)
- PhasePredictor 独立集成: state → predict → result stored
- Phase 结果追加到 analysis_report
- MacroRegime 传入时 macro 维度正确反映

### FR4: 现有测试不被破坏
- 运行 `pytest tests/ -x --tb=short -q` 确保无回归

## 非功能需求
- 测试不依赖外部网络、API、文件系统
- 使用 `asyncio.run()` 测试 async 方法
- Mock 原则: 只 mock 外部依赖，不 mock PhasePredictor 内部逻辑
- 每个测试方法有清晰 docstring

## 验收标准
- [ ] 所有 29 个测试用例通过
- [ ] 现有测试套件零回归
- [ ] 测试覆盖 7 维评分、6 种 Phase 判定、低波动过滤、配置覆盖、数据不足

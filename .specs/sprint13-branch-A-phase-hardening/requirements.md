# Requirements: sprint13-branch-A-phase-hardening

## 概述
PhasePredictor 硬化：8 项任务覆盖参数化、算法替换、性能优化、新字段和测试补全。

## 功能需求

### FR1 (A6): 测试 Native Async 迁移
- `pyproject.toml` 添加 `[tool.pytest.ini_options]` 下 `asyncio_mode = "auto"`
- 所有 test 函数改为 `async def`，`asyncio.run(p.predict(...))` 替换为 `await p.predict(...)`
- `conftest.py` 中 fixture 如需异步则标注 `@pytest_asyncio.fixture`
- 验收: `pytest tests/ -v` 全部通过，无 DeprecationWarning

### FR2 (A3): 标准 ADX 替换
- 新增 `_calculate_adx(highs, lows, closes, period=14) -> float` 方法，实现 Wilder's 标准 ADX
- 实现: TR → +DM/-DM → Smoothed → DX → ADX
- 替换 `_score_trend_momentum()` 中的 `_estimate_adx` proxy 调用
- 如果输入 bars < period * 2，fallback 到旧 proxy
- 验收: ADX 范围 0-100，趋势明显时 >25，震荡时 <20

### FR3 (A2): RSI 增量计算优化
- 添加实例属性 `_rsi_state: dict` 缓存 (avg_gain, avg_loss, last_close)
- 新增 `_calculate_rsi_incremental(close: float) -> float` 方法
- `_rsi_state` 为空时回退到全量计算并初始化 state
- `_score_velocity()` 中替换 RSI 调用
- 约束: 向后兼容，state 不匹配时自动 reset
- 验收: 新增 2 条 test（短序列与长序列结果一致性对比）

### FR4 (A1): Velocity/Acceleration Sensitivity 参数化
- 定义 ClassVar 常量: `VELOCITY_SENSITIVITY`, `ACCELERATION_SENSITIVITY`, `RSI_CHANGE_SENSITIVITY`
- `predict()` 入口处尝试从 config 读取，fallback 到 ClassVar 默认值
- 替换 `_score_velocity()` 和 `_score_acceleration()` 中所有硬编码数字
- 验收: 默认行为不变，既有 29 tests 全部通过

### FR5 (A7): confidence 输出字段
- `TrendPhaseResult` 新增 `confidence: float = Field(default=50.0, ge=0, le=100)`
- `predict()` 计算所有 normalized dimension scores 的标准差
- `confidence = max(0, min(100, 100 - stdev * 2.5))`
- 新增 2 条测试: uniform scores → high confidence; divergent scores → low confidence

### FR6 (A8): phase_transition_signal
- PhasePredictor 新增实例属性 `_last_phase: WyckoffPhase | None = None`
- `TrendPhaseResult` 新增 `transition: str | None = Field(default=None)`
- `predict()` 中检测 phase 变化，设置 `result.transition = f"{old}→{new}"`
- 新增 3 条测试: first call no transition、phase change produces signal、same phase no transition

### FR7 (A4): Valuation 维度测试补全
- 新增 `TestValuationScoring` class，4 条测试:
  - high PE → low score (< 40)
  - low PE → high score (> 60)
  - missing fundamentals → neutral (50)
  - normal PE → moderate (45-55)
- 需要为 predictor fixture 注入 fundamentals mock data

### FR8 (A5): _determine_phase Edge-case 组合测试
- 新增 `TestDeterminePhaseEdgeCases` class，7 条测试:
  - score == markup_threshold → markup
  - score == markdown_threshold → markdown
  - score == bullish_boundary → accumulation
  - score == bearish_boundary → distribution
  - all dims = 0 → markdown
  - all dims = 100 → markup
  - mixed extreme scores → weighted decision

## 非功能需求
- `ruff check` 0 errors
- `mypy --strict` 0 errors
- 所有新方法有 docstring + type annotations
- 测试不依赖外部网络/API/文件系统

## 验收标准与验证方式
| AC | 描述 | 验证方式 |
|----|------|---------|
| AC1 | 既有 29 tests 全部 PASS | `pytest tests/ -v` |
| AC2 | 新增约 15 条测试，总计约 44 tests | `pytest tests/ --collect-only` |
| AC3 | ruff check 0 errors | `ruff check src/agents/quant_brain/phase_predictor.py` |
| AC4 | mypy strict 0 errors | `mypy src/agents/quant_brain/phase_predictor.py --strict` |
| AC5 | A3 ADX 范围 0-100 | 单元测试断言 |
| AC6 | A2 RSI 增量与全量结果一致 | 新增对比测试 |
| AC7 | A7 confidence 范围 0-100 | 单元测试断言 |
| AC8 | A8 transition 信号正确 | 单元测试断言 |

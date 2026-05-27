# Requirements: sprint12-phase-config

## 概述
将 PhasePredictor 的权重、阈值从硬编码迁移到 `src/config.py` 配置系统，新增 `PhaseConfig` + `PhaseThresholds` 配置模型，实现 enabled 开关和低波动过滤。

## 功能需求

### FR1: PhaseConfig 配置模型
在 `src/config.py` 中新增 `PhaseThresholds` 和 `PhaseConfig` 两个 Pydantic v2 BaseModel，并在 `AlgorithmConfig` 中添加 `phase: PhaseConfig` 字段。

**AC1.1**: `get_config().algorithm.phase` 返回 `PhaseConfig` 实例，包含所有默认字段
- 验证方式: `python -c "from src.config import get_config; c = get_config(); assert hasattr(c.algorithm, 'phase'); print(c.algorithm.phase.model_dump_json(indent=2))"`

**AC1.2**: `PhaseThresholds` 包含 `markup_threshold`(70.0), `markdown_threshold`(30.0), `bullish_boundary`(60.0), `bearish_boundary`(40.0), `volume_confirm_threshold`(60.0)
- 验证方式: 检查 `get_config().algorithm.phase.thresholds` 各字段默认值

**AC1.3**: `PhaseConfig` 包含 `enabled`(True), `weights`(5维 dict), `low_volatility_threshold`(0.005), `low_volatility_neutral_score`(50.0), `min_ohlcv_bars`(50), `thresholds`(PhaseThresholds)
- 验证方式: 检查 `get_config().algorithm.phase` 各字段默认值

**AC1.4**: `PhaseConfig.validate_weights()` 验证权重之和 ≈ 1.0（容差 0.001）
- 验证方式: `assert get_config().algorithm.phase.validate_weights()`

**AC1.5**: 环境变量 `AEGIS_ALGORITHM__PHASE__ENABLED=false` 可覆盖 enabled
- 验证方式: 设置环境变量后创建 Config，检查 `c.algorithm.phase.enabled == False`

### FR2: PhasePredictor 从 Config 读取参数
修改 `phase_predictor.py`，`__init__` 接受可选 `config: PhaseConfig` 参数，默认从 `get_config().algorithm.phase` 获取。

**AC2.1**: `PhasePredictor()` 无参构造时自动从 `get_config()` 读取配置
- 验证方式: 构造实例后检查 `self._config` 和 `self._weights` 非空

**AC2.2**: `PhasePredictor(config=custom_config)` 使用传入的配置
- 验证方式: 传入 `PhaseConfig(enabled=False)`，调用 `predict([])` 返回 disabled 结果

**AC2.3**: `PhasePredictor(weights=custom_weights)` 仍可覆盖权重（向下兼容）
- 验证方式: 传入自定义 weights dict，检查 `self._weights` 为自定义值

**AC2.4**: `_determine_phase()` 使用 `self._thresholds` 而非硬编码常量（70/30/60/40）
- 验证方式: 代码审查 — 方法内引用 `self._thresholds.markup_threshold` 等

### FR3: Enabled 开关
`PhasePredictor.predict()` 在 `self._config.enabled == False` 时返回禁用结果。

**AC3.1**: `enabled=False` 时返回 `TrendPhaseResult(phase=ACCUMULATION, confidence=0.0, composite_score=50.0, phase_description="Phase predictor disabled")`
- 验证方式: 构造 `PhaseConfig(enabled=False)`，调用 `predict([])`，断言结果

**AC3.2**: `agent.py` 的 `_run_phase_predictor()` 在 `phase_config.enabled == False` 时提前返回，不创建 PhasePredictor 实例
- 验证方式: 代码审查 — agent.py 中有 enabled 检查

### FR4: 低波动过滤
当 ATR(14)/close < `low_volatility_threshold` 时，触发中性覆盖。

**AC4.1**: 极低波动数据（价格几乎不动）触发 `low_volatility_override=True`
- 验证方式: 构造 60 根价格在 99.99-100.01 范围的 OHLCV，调用 predict，断言 `result.low_volatility_override == True`

**AC4.2**: 低波动触发时 composite_score 设为 `low_volatility_neutral_score`(默认 50.0)，confidence 降为 0.3
- 验证方式: 同上测试，断言 `result.composite_score == 50.0` 且 `result.confidence == 0.3`

**AC4.3**: 低波动触发时仍计算各维度得分（用于诊断）
- 验证方式: 断言 `len(result.dimension_scores) == 5`

**AC4.4**: 正常波动数据不触发低波动覆盖
- 验证方式: 使用正常 OHLCV 数据，断言 `result.low_volatility_override == False`

### FR5: 向后兼容
现有调用方式不被破坏。

**AC5.1**: `PhasePredictor()` 无参构造行为与当前一致（使用默认权重和阈值）
- 验证方式: 构造实例，检查 `self._weights` 与 `DEFAULT_WEIGHTS` 一致

**AC5.2**: `agent.py` 中 `_run_phase_predictor()` 正常路径行为不变
- 验证方式: 现有集成测试通过

**AC5.3**: `pytest tests/ -x --tb=short` 全部通过
- 验证方式: 运行测试套件

## 非功能需求

### NFR1: 代码风格
- 所有新增配置字段使用 `Field(description=...)` 注释
- `PhaseConfig.validate_weights()` 是普通方法，非 pydantic validator
- 环境变量命名遵循 `AEGIS_ALGORITHM__PHASE__<FIELD>` 模式

### NFR2: 线程安全
- Config 读取沿用现有 `get_config()` 单例 + `_config_lock` 模式，不引入新的并发问题

## 边界场景

| 场景 | 预期行为 |
|------|---------|
| `weights` 为空 dict | `_compute_all_dimensions` 返回空列表，composite_score=0 |
| `weights` 包含未知维度名 | 未知维度被跳过（scorer_map 中不存在），不影响其他维度 |
| `low_volatility_threshold=0` | 永不触发低波动覆盖（ATR/close 不可能 < 0） |
| `min_ohlcv_bars=0` | 空数据也通过数据量检查（但可能在其他步骤出错） |
| 环境变量覆盖嵌套阈值 `AEGIS_ALGORITHM__PHASE__THRESHOLDS__MARKUP_THRESHOLD=75.0` | pydantic_settings 自动生效 |
| `validate_weights()` 权重和不等于 1.0 | 返回 False，不抛异常（仅警告级别） |

## Out of Scope
- **velocity 和 acceleration 维度**: 当前 PhasePredictor 仅有 5 维 scorer（trend_momentum, volume, mean_reversion, macro, valuation）。spec 中提到的 7 维权重（含 velocity, acceleration）需要新增 scorer 方法，属于新功能开发，不在本次"外部化配置"范围内。本次保持 5 维权重。
- **`_compute_all_dimensions()` 中的 velocity/acceleration scorer**: 同上，不实现。
- **配置热更新**: 不支持运行时动态修改配置，需重启生效。
- **PhaseConfig 的 pydantic validator**: `validate_weights()` 是普通方法，不在 model_validator 中自动调用。

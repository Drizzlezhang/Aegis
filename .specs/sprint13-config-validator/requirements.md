# Requirements: sprint13-config-validator

## 概述
为 PhaseConfig 添加 pydantic `@model_validator` 强制权重归一化校验，新增 sensitivity/cooldown/period 参数，编写单元测试。

## 功能需求

### FR1: @model_validator 强制权重归一化
将 `validate_weights()` 从普通方法升级为 `@model_validator(mode='after')`，在 PhaseConfig 构造时自动校验权重之和。

**AC1.1**: 默认权重（7 维，sum=1.0）构造成功
- 验证方式: `PhaseConfig()` 不抛异常

**AC1.2**: 权重 sum < 0.99 时抛出 ValidationError
- 验证方式: `PhaseConfig(weights={"trend_momentum": 0.5, "velocity": 0.1})` → ValidationError

**AC1.3**: 权重 sum > 1.01 时抛出 ValidationError
- 验证方式: `PhaseConfig(weights={"trend_momentum": 0.5, "velocity": 0.3, "acceleration": 0.3})` → ValidationError

**AC1.4**: 权重 sum 在容差范围内（如 0.995）通过校验
- 验证方式: 构造 sum=0.995 的 weights，不抛异常

**AC1.5**: 保留原 `validate_weights()` 方法（向后兼容，标注 deprecated）
- 验证方式: `PhaseConfig().validate_weights()` 返回 True

### FR2: Sensitivity 参数扩展
PhaseConfig 新增 velocity_sensitivity、acceleration_sensitivity、rsi_change_sensitivity 三个字段。

**AC2.1**: 默认值正确：velocity_sensitivity=2000.0, acceleration_sensitivity=500.0, rsi_change_sensitivity=1.667
- 验证方式: `PhaseConfig()` 检查三个字段默认值

**AC2.2**: sensitivity 字段 gt=0 约束生效，负值抛出 ValidationError
- 验证方式: `PhaseConfig(velocity_sensitivity=-1.0)` → ValidationError

**AC2.3**: 自定义 sensitivity 值可正确设置
- 验证方式: `PhaseConfig(velocity_sensitivity=3000.0)` → config.velocity_sensitivity == 3000.0

**AC2.4**: 环境变量 `AEGIS_ALGORITHM__PHASE__VELOCITY_SENSITIVITY=5000` 可覆盖
- 验证方式: 设置环境变量后 `get_config().algorithm.phase.velocity_sensitivity == 5000.0`

### FR3: Phase Transition Cooldown 参数
PhaseConfig 新增 phase_transition_cooldown_bars 字段。

**AC3.1**: 默认值 = 3
- 验证方式: `PhaseConfig().phase_transition_cooldown_bars == 3`

**AC3.2**: 范围约束 ge=1, le=20 生效
- 验证方式: `PhaseConfig(phase_transition_cooldown_bars=0)` → ValidationError；`PhaseConfig(phase_transition_cooldown_bars=25)` → ValidationError

### FR4: ADX/RSI Period 参数
PhaseConfig 新增 adx_period、rsi_period 字段。

**AC4.1**: 默认值 adx_period=14, rsi_period=14
- 验证方式: `PhaseConfig()` 检查两个字段默认值

**AC4.2**: 范围约束 ge=7, le=30 生效
- 验证方式: `PhaseConfig(adx_period=5)` → ValidationError

### FR5: 单元测试
新建 PhaseConfig 验证测试。

**AC5.1**: 9 个测试用例全部通过
- 验证方式: `pytest tests/test_config.py -v -k "PhaseConfig"` → 9 passed

### FR6: 回归验证
既有功能不受影响。

**AC6.1**: 既有 29 phase predictor tests 通过
- 验证方式: `pytest tests/agents/test_phase_predictor.py -v` → 29 passed

**AC6.2**: `ruff check src/config.py` 0 errors
- 验证方式: 运行 ruff check

## 非功能需求

### NFR1: 代码风格
- 使用 `from pydantic import model_validator` + `from typing import Self`
- `validate_weights()` 保留并标注 `@deprecated`

### NFR2: 向下兼容
- 字段名保持 `weights`（非 `dimension_weights`）
- 环境变量前缀保持 `AEGIS_ALGORITHM__PHASE__`（非 `AEGIS_PHASE__`）
- 所有新字段有默认值，不传时行为不变

## 边界场景

| 场景 | 预期行为 |
|------|---------|
| weights 为空 dict | sum=0，抛出 ValidationError |
| weights 缺少某些维度 | sum < 1.0，抛出 ValidationError |
| sensitivity=0 | gt=0 约束，抛出 ValidationError |
| cooldown=1（边界值） | 通过校验 |
| cooldown=20（边界值） | 通过校验 |
| adx_period=7（边界值） | 通过校验 |
| adx_period=30（边界值） | 通过校验 |

## Out of Scope
- PhasePredictor 中使用 sensitivity/cooldown/period 参数（由后续 Branch A/C 实现）
- 环境变量前缀改为 `AEGIS_PHASE__`（保持现有 `AEGIS_ALGORITHM__PHASE__`）
- 字段重命名为 `dimension_weights`（保持现有 `weights`）

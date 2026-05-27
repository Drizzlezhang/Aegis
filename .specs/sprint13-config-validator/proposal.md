# Change: sprint13-config-validator

## 概述
为 PhaseConfig 添加 pydantic `@model_validator` 强制权重归一化校验，新增 sensitivity/cooldown/period 参数扩展，并编写对应单元测试。

## 动机
当前 `PhaseConfig.validate_weights()` 是普通方法，可构造非法 config 而不报错。需要改为 `@model_validator(mode='after')` 在构造时强制校验。同时为支撑后续 Branch A/C 需求，新增 velocity_sensitivity、acceleration_sensitivity、rsi_change_sensitivity、phase_transition_cooldown_bars、adx_period、rsi_period 参数。

## 影响范围
- `src/config.py` — 修改 PhaseConfig：添加 @model_validator、新增 6 个字段
- `tests/test_config.py` — 新增 PhaseConfig 验证测试（9 个用例）

## 验收目标
| # | 条件 |
|---|------|
| 1 | 权重 sum < 0.99 或 > 1.01 时构造 PhaseConfig 抛出 ValidationError |
| 2 | 默认权重通过校验（sum=1.0） |
| 3 | sensitivity 字段 gt=0 约束生效 |
| 4 | cooldown 字段 ge=1, le=20 约束生效 |
| 5 | 既有 29 phase predictor tests 不受影响 |
| 6 | `ruff check src/config.py` 0 errors |

## Size: S
## 推断依据
- 范围：单模块（config）+ 测试扩展
- 关键词：`validator`、`config`、`sensitivity`、`cooldown`
- 预估文件数：2（1 修改 + 1 测试新增）
- 依赖变更：无新增外部依赖
- 风险：低（仅添加 validator 和新字段，默认值不变，向下兼容）

## 阶段序列
0 → 1 → 4 → 5 → 6

# Change: sprint12-phase-config

## 概述
将 PhasePredictor 的权重、阈值从硬编码迁移到 `src/config.py` 配置系统，新增 `PhaseConfig` + `PhaseThresholds` 配置模型，实现 enabled 开关和低波动过滤（ATR/close < threshold → 中性输出）。

## 动机
Branch A (phase-predictor-core) 已将 PhasePredictor 5 维 Wyckoff 引擎合入 master，但权重（DEFAULT_WEIGHTS）和阈值（low_vol_threshold）仍硬编码在 `phase_predictor.py` 中。需要外部化到配置系统，支持环境变量覆盖和运行时调整。

## 影响范围
- `src/config.py` — 新增 `PhaseThresholds`、`PhaseConfig`，修改 `AlgorithmConfig` 添加 `phase` 字段
- `src/agents/quant_brain/phase_predictor.py` — 修改 `__init__` 从 config 读取，新增 `_check_low_volatility()`、`_compute_all_dimensions()`，修改 `_determine_phase()` 使用配置阈值
- `src/agents/quant_brain/agent.py` — 修改 `_run_phase_predictor()` 添加 enabled 检查，传递 config

## 验收目标
| # | 条件 |
|---|------|
| 1 | `get_config().algorithm.phase` 存在且有正确默认值 |
| 2 | 默认权重验证通过（sum ≈ 1.0） |
| 3 | `PhaseConfig(enabled=False)` 时 predict 返回 disabled 结果 |
| 4 | 低波动数据触发 `low_volatility_override=True` |
| 5 | 现有测试不被破坏 |

## Size: S
## 推断依据
- 范围：单模块（quant_brain）+ config 扩展
- 关键词：`config`、`externalize`、`weights`、`thresholds`
- 预估文件数：3（3 修改）
- 依赖变更：无新增外部依赖
- 风险：低（向下兼容，不传 config 时自动从 get_config() 获取）

## 阶段序列
0 → 1 → 4 → 5 → 6

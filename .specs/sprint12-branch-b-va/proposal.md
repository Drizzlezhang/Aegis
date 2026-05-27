# Change: sprint12-branch-b-va

## 概述
扩展 PhasePredictor 从 5 维到 7 维，新增 Velocity（趋势速度）和 Acceleration（趋势加速度）两个维度。

## 动机
当前 PhasePredictor 仅覆盖 5 个维度（trend_momentum, volume, mean_reversion, macro, valuation），缺少对趋势变化速率和加速度的度量。新增 velocity/acceleration 维度可提升 Wyckoff 相位分类的精度，尤其在趋势转折点附近。

## 影响范围
- `src/agents/quant_brain/phase_predictor.py` — 新增 `_score_velocity()`、`_score_acceleration()`，更新 `DEFAULT_WEIGHTS`，更新 `predict()` 维度路由
- `src/agents/quant_brain/agent.py` — 无需修改（`predict()` 接口不变，`dimension_scores` 列表自然扩展）
- `src/models/trend_phase.py` — 无需修改（`DimensionScore` 列表长度自然扩展）
- `tests/agents/test_phase_predictor.py` — 新建测试文件

## 验收目标
1. `DEFAULT_WEIGHTS` 包含 7 个维度，权重总和 = 1.0
2. 上涨趋势 OHLCV → velocity > 50
3. 加速上涨 OHLCV → acceleration > 50
4. 横盘 OHLCV → velocity ≈ 50, acceleration ≈ 50
5. 数据不足时返回中性分 50
6. 现有测试无回归

## Size: S
## 推断依据
- 范围：单模块（phase_predictor.py），仅新增 2 个方法 + 修改权重常量
- 关键词：add（新增维度）
- 预估文件数：2-3（phase_predictor.py 修改 + 新建测试文件）
- 依赖变更：仅内部，无外部依赖
- 风险：无破坏性，predict() 接口不变

## 阶段序列
0 → 1 → 4 → 5 → 6（S 跳过 DESIGN/PLAN）

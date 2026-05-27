# Requirements: sprint12-branch-b-va

## 功能需求

### FR-1: Velocity 维度
**来源**: Task 1.2 — 新增 `_score_velocity()` 方法

- **Given** PhasePredictor 收到 >= 25 根 OHLCV bar
- **When** 调用 `_score_velocity(ohlcv_data)`
- **Then** 返回 0-100 的 float 分数，由三个子信号加权合成：
  - EMA5/EMA20 deviation slope（权重 40%）
  - RSI change rate（权重 30%）
  - MACD histogram growth rate（权重 30%）

### FR-2: Acceleration 维度
**来源**: Task 1.3 — 新增 `_score_acceleration()` 方法

- **Given** PhasePredictor 收到 >= 30 根 OHLCV bar
- **When** 调用 `_score_acceleration(ohlcv_data)`
- **Then** 返回 0-100 的 float 分数，由三个子信号加权合成：
  - Velocity 一阶导数（权重 40%）
  - MACD histogram 二阶导数（权重 30%）
  - RSI 二阶变化率（权重 30%）

### FR-3: 权重更新
**来源**: Task 1.1 — 更新 `DEFAULT_WEIGHTS`

- **Given** 当前 DEFAULT_WEIGHTS 为 5 维
- **When** 新增 velocity/acceleration 维度
- **Then** DEFAULT_WEIGHTS 更新为 7 维，权重总和 = 1.0：
  - trend_momentum: 0.20, velocity: 0.15, acceleration: 0.12, volume: 0.18, mean_reversion: 0.15, macro: 0.10, valuation: 0.10

### FR-4: 维度路由
**来源**: Task 1.4 — 确保 `predict()` 动态路由

- **Given** `self._weights` 包含 7 个维度 key
- **When** `predict()` 遍历 `self._weights.keys()`
- **Then** 通过 scorer_map 动态调用对应的 `_score_*` 方法，不存在的 key 跳过（向下兼容 5 维配置）

### FR-5: 数据不足降级
**来源**: Task 1.5 — 数据长度校验

- **Given** OHLCV 数据 < 25 根（velocity）或 < 30 根（acceleration）
- **When** 调用对应 scorer
- **Then** 返回 50.0（中性），不影响其他维度

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: DEFAULT_WEIGHTS 含 7 维且总和=1.0 | `python -c "from src.agents.quant_brain.phase_predictor import PhasePredictor; p = PhasePredictor(); assert 'velocity' in p.DEFAULT_WEIGHTS; assert 'acceleration' in p.DEFAULT_WEIGHTS; assert abs(sum(p.DEFAULT_WEIGHTS.values()) - 1.0) < 0.001"` |
| AC-2: 上涨趋势 velocity > 50 | 构造 60 根线性上涨 OHLCV，调用 `_score_velocity()`，断言 > 50 |
| AC-3: 加速上涨 acceleration > 50 | 构造 60 根指数上涨 OHLCV，调用 `_score_acceleration()`，断言 > 50 |
| AC-4: 横盘 velocity ≈ 50 | 构造 60 根窄幅震荡 OHLCV，调用 `_score_velocity()`，断言 40 < score < 60 |
| AC-5: 数据不足返回 50 | 传入 < 25 根 bar，调用 `_score_velocity()`，断言 == 50.0 |
| AC-6: 现有测试无回归 | `pytest tests/ -x --tb=short -q` 零新增失败 |

## 用户故事
- As a 量化分析师, I want PhasePredictor 能感知趋势变化速度（velocity），So that 我能区分"缓慢上涨"和"快速拉升"两种不同市况。
- As a 量化分析师, I want PhasePredictor 能感知趋势加速度（acceleration），So that 我能在趋势转折前捕捉到减速/加速信号。

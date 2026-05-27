# Change: sprint11-aegis-backtest-v2

## 概述
实现 Options-aware Backtest Engine，支持 covered_call / bull_spread / leaps 策略的期权收益回测；增加结果持久化和历史管理；前端新增历史列表页。

## 动机
当前回测系统仅支持基础股票回测，缺少期权策略回测能力。需要：
1. 期权定价模型（intrinsic + time decay 近似）
2. 三种期权策略回测引擎（covered_call, bull_spread, leaps）
3. 回测结果持久化（SQLite + JSON）
4. 历史管理 API 和前端页面

## 影响范围
- `src/backtest/options_pricing.py` — 新建，期权定价模型
- `src/backtest/options_engine.py` — 新建，期权回测引擎
- `src/backtest/storage.py` — 新建，回测结果持久化
- `src/api/routes/backtest.py` — 扩展，新增 history CRUD + 自动保存
- `web/app/backtest/history/page.tsx` — 新建，历史列表页
- `web/components/BacktestHistoryTable.tsx` — 新建，历史表格组件
- `web/lib/api.ts` — 新增 backtest history API 函数
- `tests/backtest/test_options_engine.py` — 新建，6 tests
- `tests/backtest/test_storage.py` — 新建，3 tests

## 验收目标
1. OptionsBacktestEngine 支持 covered_call/bull_spread/leaps 三种策略
2. POST /backtest 自动保存结果到 storage
3. GET /backtest/history 返回历史列表
4. 前端 /backtest/history 页面展示历史并可删除
5. 新增 ≥8 tests，全量回归 0 新增失败

## Size: M
## 推断依据
- 范围：跨 3 模块（backtest, api, web），~10 文件
- 关键词：feature/backtest/engine
- 预估文件数：10（4-10 → M）
- 依赖变更：仅内部
- 风险：中等（期权定价精度、回测引擎逻辑正确性）

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

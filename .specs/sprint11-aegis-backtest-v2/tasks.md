# Tasks: sprint11-aegis-backtest-v2

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: Options 定价模型
- 描述: 新建 `src/backtest/options_pricing.py`，实现 OptionType、OptionPosition、intrinsic_value、time_decay_factor、option_value_at、position_pnl
- read_files: []
- write_files: [`src/backtest/options_pricing.py`]
- verify: `python3 -m py_compile src/backtest/options_pricing.py`
- status: done

#### T02: Backtest 结果持久化
- 描述: 新建 `src/backtest/storage.py`，实现 BacktestStorage（SQLite 索引 + JSON 文件存储），含 save/list_runs/get_run/delete_run
- read_files: []
- write_files: [`src/backtest/storage.py`]
- verify: `python3 -m py_compile src/backtest/storage.py`
- status: done

### Wave 2（依赖 Wave 1）

#### T03: OptionsBacktestEngine
- 描述: 新建 `src/backtest/options_engine.py`，实现 OptionsStrategy、OptionsTradeResult、OptionsBacktestResult、OptionsBacktestEngine（含 run、_construct_legs、_compute_metrics），复用 strategies._calculate_rsi 和 metrics.calculate_metrics
- depends_on: [T01]
- read_files: [`src/backtest/strategies.py`, `src/backtest/metrics.py`]
- write_files: [`src/backtest/options_engine.py`]
- verify: `python3 -m py_compile src/backtest/options_engine.py`
- status: done

#### T04: Backtest API 扩展
- 描述: 修改 `src/api/routes/backtest.py`，新增 GET/DELETE /backtest/history 端点，修改 POST /backtest 自动保存结果到 BacktestStorage
- depends_on: [T02]
- read_files: [`src/api/routes/backtest.py`]
- write_files: [`src/api/routes/backtest.py`]
- verify: `python3 -m py_compile src/api/routes/backtest.py`
- status: done

### Wave 3（依赖 Wave 2）

#### T05: API 客户端函数
- 描述: 在 `web/lib/api.ts` 新增 BacktestRunSummary interface、getBacktestHistory、getBacktestRunDetail、deleteBacktestRun、mapBacktestRun mapper
- depends_on: [T04]
- read_files: [`web/lib/api.ts`]
- write_files: [`web/lib/api.ts`]
- verify: `cd web && npx tsc --noEmit --pretty 2>&1 | head -20`
- status: done

#### T06: BacktestHistoryTable 组件
- 描述: 新建 `web/components/BacktestHistoryTable.tsx`，MUI Table 展示历史列表，涨跌色、Chip、操作按钮
- depends_on: [T05]
- read_files: [`web/components/PositionTable.tsx`, `web/lib/change-color.ts`]
- write_files: [`web/components/BacktestHistoryTable.tsx`]
- verify: `cd web && npx tsc --noEmit --pretty 2>&1 | head -20`
- status: done

### Wave 4（依赖 Wave 3）

#### T07: 前端历史列表页
- 描述: 新建 `web/app/backtest/history/page.tsx`，调用 getBacktestHistory，渲染 BacktestHistoryTable，含筛选和删除功能
- depends_on: [T05, T06]
- read_files: [`web/app/backtest/page.tsx`, `web/components/BacktestPageContent.tsx`]
- write_files: [`web/app/backtest/history/page.tsx`]
- verify: `cd web && npx tsc --noEmit --pretty 2>&1 | head -20`
- status: done

### Wave 5（依赖 Wave 1, Wave 2）

#### T08: 后端测试
- 描述: 新建 `tests/backtest/test_options_engine.py`（6 tests）和 `tests/backtest/test_storage.py`（3 tests）
- depends_on: [T01, T03, T02]
- read_files: [`src/backtest/options_pricing.py`, `src/backtest/options_engine.py`, `src/backtest/storage.py`]
- write_files: [`tests/backtest/test_options_engine.py`, `tests/backtest/test_storage.py`]
- verify: `python3 -m pytest tests/backtest/test_options_engine.py tests/backtest/test_storage.py -v --tb=short`
- status: done

## 风险任务
- **T03 (OptionsBacktestEngine)**: 核心逻辑最复杂，covered_call 股票收益计算、退出条件判断、RSI 复用是主要风险点
- **T04 (API 扩展)**: POST /backtest 自动保存需处理 storage 写入失败的降级逻辑

## 回滚任务
- 删除 `src/backtest/options_pricing.py`、`src/backtest/options_engine.py`、`src/backtest/storage.py`
- 恢复 `src/api/routes/backtest.py` 到修改前版本
- 删除 `web/components/BacktestHistoryTable.tsx`、`web/app/backtest/history/page.tsx`
- 恢复 `web/lib/api.ts` 中新增的 backtest history 代码
- 删除 `tests/backtest/test_options_engine.py`、`tests/backtest/test_storage.py`

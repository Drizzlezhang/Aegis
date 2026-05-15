# Tasks: sprint2-session4-frontend-skills

## 执行策略
- Size = L，按完整阶段推进。
- 任务按 Wave 串并结合：先前端输入与 i18n 基础，再展示组件，再算法/API，再测试收口。
- 每个任务都附 verify 命令，完成即打勾。

## 执行结果
- [x] T1.1 新建 SymbolSearch 组件
- [x] T1.2 新增 i18n 插值工具
- [x] T1.3 扩展 interaction 文案与类型
- [x] T1.4 AnalyzeForm 接入 SymbolSearch + i18n 替换
- [x] T2.1 新建 DebatePanel 组件
- [x] T2.2 AnalyzeForm 结果区接入 DebatePanel
- [x] T3.1 扩展 BSMPricerSkill 为 price/IV 双模式
- [x] T3.2 修复 analyze_stream executionTime
- [x] T4.1 升级 AnalysisProgress 测试（受 Vitest JSX 解析限制，降级为源码断言扩展）
- [x] T4.2 新增 SymbolSearch 测试（源码断言扩展）
- [x] T4.3 新增 DebatePanel 测试（源码断言扩展）
- [x] T4.4 扩展 BSM 与 API 测试
- [x] T4.5 全量验证收口

## Wave 1 — 输入层与 i18n 基础

### T1.1 新建 SymbolSearch 组件
- 目标：实现热门 symbol + 自由输入 + 去重 + 上限 + 删除/清空。
- 读取：`web/components/AnalyzeForm.tsx`, `web/i18n/messages/interaction.ts`, `web/i18n/types.ts`
- 写入：`web/components/SymbolSearch.tsx`
- 依赖：无
- 优先级：P0
- verify:
  - `cd web && npx tsc --noEmit`

### T1.2 新增 i18n 插值工具
- 目标：支持 `{key}` 文本替换。
- 读取：`web/i18n/get-message.ts`（如需确认调用方式）
- 写入：`web/i18n/interpolate.ts`
- 依赖：无
- 优先级：P0
- verify:
  - `cd web && npx tsc --noEmit`

### T1.3 扩展 interaction 文案与类型
- 目标：补齐 AnalyzeForm/SymbolSearch/DebatePanel 文案 key（zh-CN/en）。
- 读取：`web/i18n/messages/interaction.ts`, `web/i18n/types.ts`
- 写入：`web/i18n/messages/interaction.ts`, `web/i18n/types.ts`
- 依赖：T1.2
- 优先级：P0
- verify:
  - `cd web && npx tsc --noEmit`

### T1.4 AnalyzeForm 接入 SymbolSearch + i18n 替换
- 目标：移除硬编码 symbol 区块，改接 `SymbolSearch`；统一文案走 `getMessage + interpolate`；修复 retry 点击调用方式。
- 读取：`web/components/AnalyzeForm.tsx`, `web/components/AnalysisProgress.tsx`
- 写入：`web/components/AnalyzeForm.tsx`
- 依赖：T1.1, T1.2, T1.3
- 优先级：P0
- verify:
  - `cd web && npx tsc --noEmit`

## Wave 2 — Debate 展示

### T2.1 新建 DebatePanel 组件
- 目标：解析 `analysisReport` 的 Investment Debate 段，成功则渲染，失败则 `null`。
- 读取：`web/components/AnalyzeForm.tsx`
- 写入：`web/components/DebatePanel.tsx`
- 依赖：T1.3
- 优先级：P1
- verify:
  - `cd web && npx tsc --noEmit`

### T2.2 AnalyzeForm 结果区接入 DebatePanel
- 目标：每个 symbol 结果卡先展示 debate，再展示 recommendation。
- 读取：`web/components/AnalyzeForm.tsx`, `web/components/DebatePanel.tsx`
- 写入：`web/components/AnalyzeForm.tsx`
- 依赖：T2.1
- 优先级：P1
- verify:
  - `cd web && npx tsc --noEmit`

## Wave 3 — BSM 与 SSE executionTime

### T3.1 扩展 BSMPricerSkill 为 price/IV 双模式
- 目标：抽取 `_bsm_price`，新增 `_solve_implied_volatility` + `_bisection_iv`，并支持 `mode`。
- 读取：`skills/algorithms/bsm_pricer/skill.py`
- 写入：`skills/algorithms/bsm_pricer/skill.py`
- 依赖：无
- 优先级：P0
- verify:
  - `python3 -m py_compile skills/algorithms/bsm_pricer/skill.py`
  - `python3 -c "from skills.algorithms.bsm_pricer.skill import BSMPricerSkill; print('BSM OK')"`

### T3.2 修复 analyze_stream executionTime
- 目标：按 symbol 真实耗时回填 `AnalyzeResult.executionTime`。
- 读取：`src/api/routes/analyze_stream.py`
- 写入：`src/api/routes/analyze_stream.py`
- 依赖：无
- 优先级：P0
- verify:
  - `python -c "from src.api.routes.analyze_stream import router; print('OK')"`（必要时带 PYTHONPATH）

## Wave 4 — 测试升级与回归

### T4.1 升级 AnalysisProgress 测试
- 目标：优先组件级测试（若依赖不足则降级扩展文本断言），覆盖 render/progress/error/retry/unmount-cleanup。
- 读取：`web/tests/components/analysis-progress.test.ts`, `web/components/AnalysisProgress.tsx`
- 写入：`web/tests/components/analysis-progress.test.ts`
- 依赖：T1.4
- 优先级：P0
- verify:
  - `cd web && npx vitest run tests/components/analysis-progress.test.ts --reporter=verbose`

### T4.2 新增 SymbolSearch 测试
- 目标：覆盖热门点击、自定义输入、规范化、去重、上限。
- 读取：`web/components/SymbolSearch.tsx`
- 写入：`web/tests/components/symbol-search.test.ts`
- 依赖：T1.1
- 优先级：P0
- verify:
  - `cd web && npx vitest run tests/components/symbol-search.test.ts --reporter=verbose`

### T4.3 新增 DebatePanel 测试
- 目标：覆盖正常解析、空文本、异常格式、i18n 切换。
- 读取：`web/components/DebatePanel.tsx`
- 写入：`web/tests/components/debate-panel.test.ts`
- 依赖：T2.1
- 优先级：P1
- verify:
  - `cd web && npx vitest run tests/components/debate-panel.test.ts --reporter=verbose`

### T4.4 扩展 BSM 与 API 测试
- 目标：新增 IV round-trip/deep OTM/invalid price；补 executionTime 断言。
- 读取：`tests/test_bsm_pricer.py`, `tests/api/test_analyze_stream.py`
- 写入：`tests/test_bsm_pricer.py`, `tests/api/test_analyze_stream.py`
- 依赖：T3.1, T3.2
- 优先级：P0
- verify:
  - `python -m pytest tests/test_bsm_pricer.py tests/api/test_analyze_stream.py -x -v`

### T4.5 全量验证收口
- 目标：执行 sprint 要求验证矩阵并记录证据。
- 读取：所有受影响文件
- 写入：`.specs/sprint2-session4-frontend-skills/verification.md`
- 依赖：T1~T4 全部
- 优先级：P0
- verify:
  - `python3 -m py_compile skills/algorithms/bsm_pricer/skill.py`
  - `python -m pytest tests/test_bsm_pricer.py tests/api/test_analyze_stream.py -x -v`
  - `cd web && npx tsc --noEmit`
  - `cd web && npm run build`
  - `cd web && npx vitest run --reporter=verbose`

## 依赖关系摘要
- T1.1/T1.2/T1.3 → T1.4
- T1.3 → T2.1 → T2.2
- T3.1/T3.2 → T4.4
- T1.4 → T4.1
- T1.1 → T4.2
- T2.1 → T4.3
- T4.1/T4.2/T4.3/T4.4 → T4.5

## 回滚任务（仅在 VERIFY 失败时启用）
- R1: 回退 `AnalyzeForm` 到 Sprint1 结果视图结构。
- R2: 撤销 `DebatePanel` 接入，仅保留 recommendation 渲染。
- R3: 撤销 IV 模式扩展，恢复 price-only。
- R4: 撤销 executionTime 计时补丁。

# Requirements: sprint2-session4-frontend-skills

## 功能需求
### FR-1: SSE 生命周期修复
- Given: `AnalysisProgress` 正在消费 SSE 流。
- When: 组件卸载或视图切换。
- Then: 通过 `AbortController` 终止流读取，不再触发卸载后的状态更新。

### FR-2: Symbol 搜索与自定义输入
- Given: 用户在 AnalyzeForm 选择标的。
- When: 使用搜索、热门列表、回车或逗号输入自定义 ticker。
- Then: 结果按大写规范化、去重，且最大数量受限（默认 20）。

### FR-3: AnalyzeForm i18n 全覆盖
- Given: locale 为 `zh-CN` 或 `en`。
- When: 渲染 AnalyzeForm / SymbolSearch / DebatePanel。
- Then: 用户可见文案全部走 `getMessage`，动态文本通过 `interpolate()` 插值。

### FR-4: DebatePanel 展示辩论结论
- Given: `analysisReport` 包含 `## Investment Debate` 段。
- When: 结果页渲染 symbol 卡片。
- Then: 展示 bull/bear 论点、verdict、winning side、confidence；无法解析时不渲染组件。

### FR-5: BSM 隐含波动率求解
- Given: `mode=implied_volatility` 且输入 `market_price`。
- When: 调用 `BSMPricerSkill.execute()`。
- Then: 先 Newton-Raphson 迭代，vega 过小时切到 bisection fallback，返回 `implied_volatility/iterations/converged/method`。

### FR-6: BSM 定价逻辑复用与纯 Python约束
- Given: price 与 IV 两种模式都需使用 BSM 核心计算。
- When: 运行 skill。
- Then: 核心公式复用内部方法，不引入 scipy/numpy。

### FR-7: SSE executionTime 修复
- Given: `/api/analyze/stream` 返回 `result` 事件。
- When: 每个 symbol pipeline 完成。
- Then: `executionTime` 为该 symbol 实际耗时（秒，round 到 2 位），不再固定 `0.0`。

### FR-8: 测试升级
- Given: Sprint 2 新增能力已接入。
- When: 运行指定 pytest/vitest/build/type 命令。
- Then: 新老关键路径都通过。

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 卸载时 SSE 可中断且不触发卸载后更新 | `web/tests/components/analysis-progress.test.ts` 覆盖 unmount/abort 场景；组件级或扩展文本测试断言包含 AbortController 传递与 cleanup |
| AC-2: SymbolSearch 支持热门+自由输入+去重+上限 | `web/tests/components/symbol-search.test.ts` 覆盖点击、输入、规范化、去重、max 限制 |
| AC-3: AnalyzeForm/SymbolSearch/DebatePanel 文案双语可用 | `web/i18n/messages/interaction.ts` 与 `web/i18n/types.ts` key 对齐检查 + 组件测试切换 locale 断言 |
| AC-4: DebatePanel 可解析辩论文本并在异常时 graceful fallback | `web/tests/components/debate-panel.test.ts` 覆盖正常/空文本/异常文本 |
| AC-5: BSM IV 反解可收敛，ATM round-trip 在容差内 | `python -m pytest tests/test_bsm_pricer.py -x -v` 中新增 IV 用例（ATM/deep OTM/invalid price） |
| AC-6: BSM 保持纯 Python 无 scipy/numpy 依赖 | `python3 -m py_compile skills/algorithms/bsm_pricer/skill.py` + `rg -n "scipy|numpy" skills/algorithms/bsm_pricer/skill.py` |
| AC-7: `/api/analyze/stream` 返回真实 executionTime 与既有事件序列正确 | `python -m pytest tests/api/test_analyze_stream.py -x -v`（补 executionTime 断言） |
| AC-8: 前端构建、类型与测试通过 | `cd web && npm run build`、`cd web && npx tsc --noEmit`、`cd web && npx vitest run --reporter=verbose` |
| AC-9: 热修复项不回退（AbortController、死 import 删除） | diff 检查 `web/components/AnalysisProgress.tsx`, `web/lib/api.ts`, `src/api/routes/analyze_stream.py` 保持修复状态 |

## 非功能需求
- NFR-1: 领地约束严格遵守，仅改 `web/`, `skills/algorithms/bsm_pricer/`, `src/api/routes/analyze_stream.py`, `tests/` 指定文件。
- NFR-2: 不新增重型 i18n 或数值库。
- NFR-3: 组件行为可测，优先 vitest；若缺 testing-library 依赖，保持可执行降级测试策略并明确记录。

## 边界场景
- Edge-1: 空 symbol 集合，Analyze 按钮禁用并提示。
- Edge-2: 输入包含空字符串、重复、小写、逗号分隔混合，输出应规范化。
- Edge-3: Debate markdown 格式不完整，组件不崩溃。
- Edge-4: IV 求解遇到极低 vega，触发 bisection fallback。
- Edge-5: market_price <= 0，返回错误结果而非异常崩溃。

## Out of Scope
- 不实现持仓监控新面板（仅补 `position_alerts_title` i18n key）。
- 不改 Agent 编排与 LLM 路由。
- 不新增 DB schema 或权限模型。

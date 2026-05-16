# Design: sprint2-session4-frontend-skills

## 技术方案概述
本次 Sprint 2 Session 4 采用“前端体验增强 + 数值能力扩展 + 流协议修正 + 测试升级”四轨并行方案：
1. 前端：引入 `SymbolSearch` 与 `DebatePanel`，并将 `AnalyzeForm` 完整 i18n 化。
2. SSE：保持 Sprint 1 hotfix（AbortController + cleanup + dead import 清理），并修复 result `executionTime`。
3. Skill：在 `BSMPricerSkill` 增加 implied volatility 模式，Newton-Raphson 主路径 + bisection fallback。
4. 测试：前端组件测试覆盖交互与解析，后端测试覆盖 IV 与 executionTime。

目标：不改 orchestrator、不增重依赖，在既有边界内完成可验证交付。

## 模块职责拆分

### 1) `web/components/SymbolSearch.tsx`（新增）
职责：symbol 选择输入边界层。
- 输入：`selected: string[]`, `onChange: (symbols: string[]) => void`, `maxSymbols?: number`
- 行为：
  - 热门列表快捷添加
  - 文本输入（Enter/逗号提交）
  - 大写标准化、去重、空值过滤
  - 上限限制（默认 20）
  - 已选 Chip 展示 + 删除 + clear all
- 输出：仅通过 `onChange` 回写，不耦合分析请求。

### 2) `web/components/DebatePanel.tsx`（新增）
职责：从 `analysisReport` 解析并展示 Investment Debate。
- 输入：`debateText: string`, `locale`
- 行为：
  - 提取 `## Investment Debate` 到下一个 `##` 之间文本
  - 正则解析 bull/bear/verdict/winning side/confidence/reasoning
  - 解析失败或文本为空时 `return null`
- 输出：纯展示组件，不改结果数据结构。

### 3) `web/components/AnalyzeForm.tsx`（修改）
职责：页面组合层。
- 使用 `SymbolSearch` 替换硬编码 symbol pill。
- 结果区在 recommendation 列表前插入 `DebatePanel`。
- 所有可见文本改为 `getMessage(...)` + `interpolate(...)`。
- 修复 `handleRetry` 触发方式，避免 `onClick` 直接透传 async 引发未处理 rejection。

### 4) `web/i18n/interpolate.ts`（新增）
职责：轻量占位符插值。
- `interpolate(template, values)` 仅做 `{key}` 替换。
- 不引入新框架，保持现有 i18n 方案。

### 5) `skills/algorithms/bsm_pricer/skill.py`（修改）
职责：price + IV 双模式统一入口。
- `execute()` 根据 `mode` 分派：`price` / `implied_volatility`。
- 抽出 `_bsm_price(...)` 复用价格与 Greeks 计算。
- `_solve_implied_volatility(...)`：
  - 初值 `sigma=0.3`
  - Newton-Raphson 迭代（容差 `1e-6`，最多 100 次）
  - 低 vega 时切换 `_bisection_iv(...)`（最多 200 次）
- 维持纯 Python（`math`），不引入 scipy/numpy。

### 6) `src/api/routes/analyze_stream.py`（修改）
职责：SSE result 序列化时补真实 executionTime。
- 在 symbol pipeline 第一步启动时记录 start 时间。
- 在 `pipeline_completed` 生成 result 时计算 `elapsed`。
- `AnalyzeResult.executionTime` 输出 `round(elapsed, 2)`。

## API / 类型设计

### 前端 API 变更
- `runAnalysisStream(symbols, handlers, signal?)` 已支持 `AbortSignal`（Sprint 1 hotfix）。
- 本次不再新增协议字段，仅保证 `result.executionTime` 语义修复。

### 新增类型/数据结构
- SymbolSearch 本地 token 解析函数：
  - `normalizeSymbol(raw: string): string`
  - `tokenizeInput(raw: string): string[]`
- DebatePanel 解析结果：
```ts
interface DebateViewModel {
  bullConfidence?: number;
  bearConfidence?: number;
  verdict?: string;
  winningSide?: string;
  verdictConfidence?: number;
  reasoning?: string;
  bullPoints: string[];
  bearPoints: string[];
}
```

## 关键流程

### 流程 A：Symbol 选择
1. 用户点击热门 symbol 或输入自定义 ticker。
2. `SymbolSearch` 规范化、去重、限额后回调 `onChange`。
3. `AnalyzeForm` 更新 selected，并用 i18n 文案显示计数。

### 流程 B：分析结果展示
1. `AnalysisProgress` 完成后切换到 results 视图。
2. 每个 symbol 卡片先渲染 `DebatePanel`（可解析时），再渲染 recommendations。
3. 字符串文案全部来自 i18n + interpolate。

### 流程 C：IV 求解
1. `mode=implied_volatility` + `market_price` 入参。
2. Newton-Raphson 主迭代。
3. 低 vega 分支进入 bisection。
4. 返回 `implied_volatility/iterations/converged` 与 method。

## 风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| Debate markdown 格式漂移 | 面板无法解析 | 解析失败直接 `return null`，不阻塞推荐展示 |
| Symbol 输入异常（空值/重复/非法字符） | 选择器状态污染 | 统一 normalize + tokenize，过滤空 token，去重 |
| IV 在极端参数下不收敛 | 输出不稳定 | NR + bisection 双轨；返回 `converged=false` 并给 method |
| executionTime 统计点错误 | 指标失真 | 以每 symbol 第一步 start 到 pipeline_completed 结束计时 |
| 前端测试环境缺依赖 | 验证中断 | 优先组件级测试；若依赖不足按要求降级并记录 |

## ADR
### ADR-1: DebatePanel 使用弱解析，不阻断主流程
- 决策：解析失败即不渲染，不抛错。
- 原因：analysisReport 文本由上游生成，格式可能波动。
- 后果：保证主结果展示稳定，牺牲少量展示完整性。

### ADR-2: IV 求解采用 NR 优先 + 二分回退
- 决策：默认 Newton-Raphson，低 vega 回退 bisection。
- 原因：NR 收敛快，bisection 更稳。
- 后果：实现复杂度小幅增加，但稳定性显著提升。

### ADR-3: i18n 插值使用自研轻量函数
- 决策：新增 `interpolate.ts`，不引入 `react-intl`。
- 原因：满足占位符需求且符合“无重依赖”约束。
- 后果：能力聚焦，维护成本低。

## 回滚计划
1. 回滚前端：移除 `SymbolSearch`/`DebatePanel` 接入，恢复 AnalyzeForm 旧结构。
2. 回滚 Skill：撤销 IV 模式与相关内部方法。
3. 回滚 API：撤销 executionTime 计时逻辑。
4. 回滚测试：删除新增测试并恢复原基线。

## Migration Plan
1. BUILD Wave 1：AnalyzeForm + SymbolSearch + i18n/interpolate。
2. BUILD Wave 2：DebatePanel + AnalyzeForm 结果区接入。
3. BUILD Wave 3：BSM IV + executionTime。
4. BUILD Wave 4：测试升级与回归。

## Observability
- 前端：Analyze 按钮计数、search 限额提示、debate 解析可见。
- 后端：SSE result 中 executionTime 可观测。
- 测试：pytest/vitest/build/type 形成完整证据链。

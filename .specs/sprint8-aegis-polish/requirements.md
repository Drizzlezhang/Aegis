# Requirements: sprint8-aegis-polish

## 功能需求

### FR-1: 策略追踪回顾页面 (Tracking Page)
**来源**: Task 1 — 新建 `web/app/tracking/page.tsx`

- **Given** 用户已登录且导航到 `/tracking` 页面
- **When** 页面加载完成
- **Then** 页面显示 4 个 Summary Cards（命中率、平均 PnL%、总追踪数、待验证数）、Strategy Breakdown Table（策略类型、数量、命中率）、Decision List Table（symbol、策略、推荐日期、入场价、目标价、状态 chip、PnL%）

- **Given** 页面已渲染且用户点击 Refresh 按钮
- **When** Refresh 触发 `POST /api/tracking/update`
- **Then** 页面重新加载 stats 与 decisions 数据并刷新展示

- **Given** Tracking 后端不可用（网络错误 / 500）
- **When** 页面加载或刷新时 API 调用失败
- **Then** 页面不崩溃，显示"—"占位或空状态提示（`trackingEmpty`）

- **Given** 决策列表中有不同 status 的记录
- **When** 页面渲染
- **Then** `hit_target` 显示绿色 chip、`hit_stop` 显示红色 chip、`expired` 显示灰色 chip、`active` 显示蓝色 chip、`pending` 显示黄色 chip

- **Given** 没有任何追踪记录
- **When** 页面加载
- **Then** 显示空状态文案："No tracked decisions yet. Recommendations will be tracked automatically."

### FR-2: Dashboard 快捷信息卡片
**来源**: Task 2 — 修改 `web/app/page.tsx`

- **Given** 用户位于 Dashboard 首页
- **When** 页面加载
- **Then** 新增 3 个卡片：Scheduler Status Card（上次运行时间、成功/失败数、高置信推荐数）、Watchlist Quick Card（数量 badge + 点击跳转 `/watchlist`）、Tracking Summary Card（命中率 + 总追踪数 + 点击跳转 `/tracking`）

- **Given** 后端数据不可用（网络错误）
- **When** 对应 API 调用失败
- **Then** 对应卡片展示"—"占位，不影响 Dashboard 页面整体渲染和其他卡片

### FR-3: 分析结果页置信度可视化
**来源**: Task 3 — 修改 `web/app/symbol/[symbol]/page.tsx` 或分析结果展示组件

- **Given** 用户查看某个 symbol 的分析结果
- **When** 策略推荐卡片的置信度 ≥ 0.8
- **Then** LinearProgress 进度条显示绿色，数字格式化展示

- **Given** 置信度在 0.6-0.8 之间
- **When** 渲染置信度组件
- **Then** LinearProgress 进度条显示黄色

- **Given** 置信度 < 0.6
- **When** 渲染置信度组件
- **Then** LinearProgress 进度条显示红色

- **Given** 高置信度推荐（≥ 0.8）
- **When** 渲染推荐卡片
- **Then** 卡片左侧 border-left: 4px solid green 高亮

- **Given** 策略推荐卡片的 symbol 在 tracking 中有记录
- **When** 渲染推荐卡片
- **Then** 卡片上显示一个小 chip "Tracked"

### FR-4: Sidebar 导航更新
**来源**: Task 4 — 修改 `web/components/Sidebar.tsx`

- **Given** 用户打开 Sidebar 导航
- **When** 渲染 NAV_ITEMS
- **Then** Tracking 入口出现在 Scheduler 和 Memory 之间，点击跳转 `/tracking`，`key` 为 `common.tracking`

### FR-5: API 层 + 类型定义
**来源**: Task 5 — 修改 `web/lib/api.ts`

- **Given** 前端需要调用 Tracking API
- **When** 调用 `getTrackingStats()`
- **Then** 内部请求 `GET /api/tracking/stats`，返回 `TrackingStats`（camelCase 映射完成）

- **Given** 前端需要获取决策列表
- **When** 调用 `getTrackedDecisions(20)`
- **Then** 内部请求 `GET /api/tracking/decisions?limit=20`，返回 `TrackedDecision[]`（camelCase 映射完成）

- **Given** 前端需要刷新追踪数据
- **When** 调用 `updateTracking()`
- **Then** 内部请求 `POST /api/tracking/update`，返回更新后的 `TrackingStats`

- **Given** 后端返回 snake_case 字段
- **When** `mapBackendStats` / `mapBackendDecision` 被调用
- **Then** 所有字段正确映射为 camelCase（hit_rate→hitRate, avg_pnl_pct→avgPnlPct 等）

### FR-6: i18n 国际化补充
**来源**: Task 6 — 修改 `web/i18n/messages/interaction.ts` + `common.ts` + `types.ts`

- **Given** 用户使用中文 / 英文界面
- **When** 渲染 tracking 页面、dashboard 卡片、置信度组件
- **Then** 所有新增文案正确显示对应语言（zh-CN / en 均定义）

- **Given** 新增 i18n key 在 types.ts 中注册
- **When** TypeScript 编译
- **Then** 所有新增 key 类型安全，无 `any` 或缺失类型

## 非功能需求

### NFR-1: 渐进降级
- 所有 Tracking API 调用必须使用 `try/catch` 包裹
- 仅网络错误时才展示降级 UI（"—"占位或空状态提示）
- 降级不得导致页面空白、崩溃或阻止其他无关组件渲染

### NFR-2: MUI 组件一致性
- 所有新增 UI（卡片、表格、chip、进度条）必须使用 MUI（Material UI）组件
- 颜色和间距保持与现有 Dashboard 页面一致

### NFR-3: API 字段映射
- 后端 snake_case → 前端 camelCase 映射必须由专用 mapper 函数完成
- mapper 不得修改原始响应对象（immutable）
- 映射参考 Sprint 7 的 `mapBackendItem` 模式

### NFR-4: 类型安全
- 所有新增 `interface` 必须严格对齐后端契约字段
- `status` 字段必须使用 union 类型，不得使用 `string`
- i18n key 必须在 types.ts 中声明，不得使用裸字符串

## 用户故事

- As a 交易员，I want to 在 `/tracking` 页面查看策略命中率与历史决策，So that 我能回顾策略表现并优化交易决策
- As a 交易员，I want to 在 Dashboard 首页看到调度状态、关注标的数与命中率概况，So that 我不用切换页面就能快速了解系统运行状态
- As a 交易员，I want to 在分析结果页看到置信度的可视化进度条，So that 我能直观判断推荐的可靠程度
- As a 交易员，I want to 通过 Sidebar 快速导航到 Tracking 页面，So that 我不需要手动输 URL

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: Tracking 页面渲染 4 个 Summary Cards + Strategy Table + Decision Table | 浏览器访问 `/tracking`，目视检查三大区域，单元测试检查 page.tsx 包含 key i18n token |
| AC-2: Refresh 按钮调用 POST /api/tracking/update 后重新加载数据 | 手动点击 Refresh，Network 面板确认 POST 请求发出且页面数据更新 |
| AC-3: Tracking 数据不可用时降级，页面不崩溃 | Mock API 返回 500，确认页面正常渲染且显示降级占位符 |
| AC-4: 5 种 status 颜色 chip 正确渲染 | 准备包含各 status 的 mock 数据，目视检查颜色映射：绿（hit_target）/ 红（hit_stop）/ 灰（expired）/ 蓝（active）/ 黄（pending）|
| AC-5: 空状态提示正确显示 | Mock 空 decisions 列表，确认显示 `trackingEmpty` 文案 |
| AC-6: Dashboard 新增 3 个快捷卡片 | 浏览器访问 Dashboard，确认 Scheduler Status / Watchlist Quick / Tracking Summary 卡片存在 |
| AC-7: Dashboard 卡片数据不可用降级 | Mock 对应 API 失败，确认卡片显示"—"占位 |
| AC-8: Watchlist 卡片点击跳转 /watchlist | 点击 Watchlist 卡片，确认路由跳转到 /watchlist |
| AC-9: Tracking Summary 卡片点击跳转 /tracking | 点击 Tracking Summary 卡片，确认路由跳转到 /tracking |
| AC-10: 置信度 ≥ 0.8 → 绿色进度条 + 数字 | 准备置信度 0.85 的 mock 数据，检查进度条颜色为 success |
| AC-11: 置信度 0.6-0.8 → 黄色进度条 | 准备置信度 0.7 的 mock 数据，检查进度条颜色为 warning |
| AC-12: 置信度 < 0.6 → 红色进度条 | 准备置信度 0.45 的 mock 数据，检查进度条颜色为 error |
| AC-13: 高置信度推荐卡片 border-left 高亮 | 检查置信度 ≥ 0.8 的卡片有 `border-left: 4px solid green` 样式 |
| AC-14: Tracking 中有记录的 symbol 显示 "Tracked" chip | Mock tracking 数据包含当前 symbol，确认 chip 渲染 |
| AC-15: Sidebar 中 Tracking 入口位于 Scheduler 和 Memory 之间 | 目视检查 Sidebar 渲染结果，确认顺序 |
| AC-16: getTrackingStats/getTrackedDecisions/updateTracking 三个函数导出 | API 单元测试检查函数存在性 |
| AC-17: snake_case → camelCase 映射正确 | API 单元测试检查 mapper 函数转换 mapBackendStats/mapBackendDecision |
| AC-18: i18n zh-CN + en 双语完整 | 切换语言后确认所有新增 key 有对应翻译；TypeScript 编译确认 key 无缺失类型 |
| AC-19: TypeScript 编译通过 | `npx tsc --noEmit` 零错误 |
| AC-20: Next.js build 成功 | `npm run build` 成功完成 |
| AC-21: 4 个前端测试通过 | `npx vitest run` tracking.test.ts + api-tracking.test.ts 全部 PASS |

## 边界场景

### Edge-1: Tracking API 完全不可用
- tracking 页面、dashboard 卡片均展示降级态
- 用户点击 Refresh 按钮后显示 toast 提示失败
- 不影响其他页面和组件的正常渲染

### Edge-2: Tracking API 返回部分数据
- 若 `stats` 正常但 `decisions` 为空，表格显示空状态
- 若 `by_strategy` 为空对象，Strategy Breakdown 表格显示空或 message
- 不因数据不完整崩溃

### Edge-3: 分析结果页置信度为 null 或 undefined
- ConfidenceBadge 组件不渲染或显示 "—" 占位
- 不因为置信度缺失而跳过整个推荐卡片

### Edge-4: 分析结果页 tracking 数据加载慢
- "Tracked" chip 在 tracking API 调用完成后才显示
- 加载期间不显示错误状态，component 不抖动

### Edge-5: 导航切换时 i18n 未加载
- 使用 i18n key 对应的 fallback 或默认文本
- 不抛出运行时异常

### Edge-6: Dashboard 中 Scheduler 数据为 null
- Scheduler Status Card 显示 "No recent scheduler runs" 占位
- 不影响其他卡片渲染

## 回滚计划
- 若 Tracking API 后端问题导致前端严重故障，可通过移除 Sidebar Tracking 入口 + 隐藏 Dashboard Tracking 卡片快速降级
- 所有新增代码集中在 `web/` 下，版本回滚只需 `git revert` 对应的 commit
- i18n 新增 key 不影响现有 key，回滚时无副作用

## 数据/权限影响
- 无用户认证变更
- 无数据库 schema 变更（纯前端）
- 新页面 `/tracking` 无额外权限要求

## 排除范围（Out of Scope）
- Python 后端修改（由 aegis-tracking / aegis-fixes 分支负责）
- Tracking 数据的实际持久化与计算逻辑
- 用户认证与权限系统
- 移动端响应式适配（后续迭代）
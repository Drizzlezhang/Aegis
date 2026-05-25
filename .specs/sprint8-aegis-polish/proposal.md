# Change: sprint8-aegis-polish

## 概述
Sprint 8 aegis-polish 分支：前端策略回顾 + 体验优化。新建 Tracking 追踪回顾页面、Dashboard 快捷卡片优化、分析结果页置信度可视化、Sidebar 导航更新、API 层 snake_case→camelCase 映射、i18n 补充，共 8 个 Task。

## 动机
Sprint 7 完成了 Scheduler + Dashboard 的集成交付。Sprint 8 需要在前端提供策略追踪回顾能力，让用户查看命中率、PnL% 等追踪数据；同时优化 Dashboard 信息密度与分析页置信度可视化，提升用户体验。

## 影响范围
- `web/app/tracking/page.tsx`（新建）
- `web/app/page.tsx`（修改，Dashboard 快捷卡片）
- `web/app/symbol/[symbol]/page.tsx` 或分析结果展示组件（修改，置信度可视化）
- `web/components/Sidebar.tsx`（修改，导航入口）
- `web/lib/api.ts`（修改，Tracking API + 类型定义）
- `web/i18n/messages/interaction.ts`（修改，新增 i18n 文案）
- `web/i18n/messages/common.ts`（修改）
- `web/i18n/types.ts`（修改）
- `web/tests/app/tracking.test.ts`（新建）
- `web/tests/lib/api-tracking.test.ts`（新建）

禁止修改：`src/` `tests/agents/` `tests/services/` `tests/llm/` `deploy/` `.github/` `skills/`

## 验收目标
1. Tracking 页面正常渲染命中率统计、分策略统计、决策列表、手动刷新
2. Dashboard 新增 3 个快捷卡片（Scheduler Status / Watchlist / Tracking Summary），数据不可用时降级
3. 分析结果页置信度可视化（LinearProgress + 颜色分级），高置信度推荐高亮
4. Sidebar 新增 Tracking 导航入口
5. API 层 snake_case→camelCase 映射正确，3 个新 API 函数可调用
6. i18n zh-CN/en 双语完整
7. 4 个前端测试通过（2 tracking page + 2 api-tracking）
8. TypeScript 编译通过，Next.js build 成功

## Size: M
## 推断依据
- 范围：跨模块前端（pages × 2 + components × 1 + API × 1 + i18n × 3 + tests × 2），约 8-10 个文件
- 关键词：feature、新建 page、修改 component、优化
- 预估文件数：8-10（含新建与修改）
- 依赖变更：新增内部 Tracking API 对接，需 snake_case→camelCase 映射 + 降级处理
- 风险：后端 tracking 可能不可用，需 try/catch 降级；置信度可视化依赖现有分析页结构

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（M 标准序列，post-spec 后触发 gate）
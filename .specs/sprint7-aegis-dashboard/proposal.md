# Change: sprint7-aegis-dashboard

## 概述
Sprint 7 前端 Dashboard：新增 Watchlist 管理页、Scheduler 调度状态页、Settings 推送配置页，更新 Sidebar 导航与 API 层，补充 i18n 文案与测试。

## 动机
Aegis 前端缺少对 watchlist 的管理界面、调度运行状态的实时可见性、以及 Telegram 推送配置入口。这三个页面补齐了用户日常操作链路：管理关注标的 → 监控分析调度 → 配置通知偏好。

## 影响范围
| 类型 | 文件 |
|------|------|
| 新建 | `web/app/watchlist/page.tsx` |
| 新建 | `web/app/scheduler/page.tsx` |
| 新建 | `web/app/settings/page.tsx` |
| 修改 | `web/components/Sidebar.tsx` |
| 修改 | `web/lib/api.ts` |
| 修改 | `web/i18n/types.ts` |
| 修改 | `web/i18n/messages/interaction.ts` |
| 新建 | `web/tests/app/watchlist.test.ts` |
| 新建 | `web/tests/app/scheduler.test.ts` |
| 新建 | `web/tests/app/settings.test.ts` |

## 边界约束
- **可修改**: `web/`
- **禁止修改**: `src/`, `tests/agents/`, `tests/services/`, `tests/llm/`, `deploy/`, `.github/`, `skills/`
- Settings 页面如后端无保存 API，降级为 localStorage 只读模式
- 保持 MUI 组件库一致性（`@mui/material` v7, `@mui/icons-material` v7）
- 保持 `zh-CN` / `en` 双语

## 验收目标
1. Watchlist 页面可添加/删除标的，支持优先级排序，含空状态提示
2. Scheduler 页面展示调度状态卡片、手动触发按钮、上次运行结果
3. Settings 页面展示 Telegram 配置与通知偏好（至少只读）
4. Sidebar 含三个新导航入口，不影响现有页面
5. API 层含 watchlist + scheduler 调用函数
6. 全部 i18n 文案覆盖中英文
7. 6 个新测试通过
8. `tsc --noEmit` + `npm run build` + `vitest run` 通过

## Size: M
## 推断依据
- 范围：单模块（`web/`）多文件，3 个新页面 + 3 类文件修改 = ~10 文件
- 关键词：`feat` 新功能开发
- 依赖：无新外部依赖，仅内部 API 层 + i18n 扩展
- 风险：前端局部修改，Settings 可降级，无破坏性

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
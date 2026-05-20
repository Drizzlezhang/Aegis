# Verification: sprint7-aegis-dashboard

## 验证时间: 2026-05-20T15:20:00+08:00

## 验证模式
- `5-full`（M 级完整验证）

## 验收标准逐条验证

| AC | 验证方式 | 状态 | 证据 |
|----|---------|------|------|
| R1: Watchlist 列表页 | vitest + build | PASS | `vitest run` 2/2 tests pass; `npm run build` 生成 `/watchlist` 路由 (7.08 kB) |
| R2: Watchlist 添加标的 | vitest | PASS | 源码含 `handleAdd`、`addToWatchlist`；表单含 TextField + Select + Button |
| R3: Watchlist 删除标的 | vitest | PASS | 源码含 `handleRemove`、`removeFromWatchlist`、`DeleteIcon` |
| R4: Scheduler 状态页 | vitest + build | PASS | `vitest run` 2/2 tests pass; `npm run build` 生成 `/scheduler` 路由 (5.86 kB) |
| R5: Scheduler "Run All Now" | vitest | PASS | 源码含 `handleRunAll`、`triggerDailyAnalysis`、`PlayArrowIcon` |
| R6: Settings 配置页 | vitest + build | PASS | `vitest run` 2/2 tests pass; `npm run build` 生成 `/settings` 路由 (14.4 kB) |
| R7: Settings localStorage 降级 | vitest | PASS | 源码含 `SETTINGS_STORAGE_KEY`、`loadSettings()`、`saveSettings()`、`handleSave` |
| R8: Sidebar 导航更新 | vitest + build | PASS | `vitest run` 2/2 sidebar tests pass; `grep` 确认 3 个新路由注册 |
| R9: API 层扩展 | tsc 类型检查 | PASS | `npx tsc --noEmit` 无错误；`grep -c` 确认 6 个函数导出 |
| R10: i18n 文案覆盖 | vitest + tsc | PASS | `vitest run` 5/5 i18n tests pass; 新增 43 个 i18n key 全部注册 |
| R11: 全量构建验证 | tsc + build | PASS | `npx tsc --noEmit` 无错误；`npm run build` 成功 |

## 测试结果
- 单元测试: **34 files / 92 tests passed** (86 existing + 6 new)
- 类型检查: `npx tsc --noEmit` — clean, 0 errors
- Build: `npm run build` — 成功，所有 3 个新路由均静态生成

## 回滚验证
- 新增页面均为独立文件，删除对应 `web/app/<route>/page.tsx` 即可恢复
- API 层新增函数为纯增量，不影响现有函数
- Sidebar NAV_ITEMS 新增 3 项，回退数组即可
- i18n 新增 key 为纯增量，不影响现有 key

## 数据/权限影响验证
- 无权限变更，新增页面使用 token 未修改
- localStorage key 使用 `aegis_watchlist` 和 `aegis_settings` 命名空间
- 无现有 localStorage key 冲突

## 总结
- **通过**: PASS (full)
- 失败项: 无
- 建议操作: 进入 6-SHIP，执行 git commit + push
# Change: aegis-settings

## 概述
Sprint 9：将前端 Settings 页面从 localStorage 切换到对接后端 Settings API，增强 Telegram 通知能力（每日 tracking 摘要），并实现配置热生效（apply_to_runtime）。

## 动机
1. 前端 Settings 当前使用 localStorage 存储配置，无法跨设备同步，且与后端 SettingsService 脱节。
2. 缺少每日 tracking 摘要的 Telegram 通知能力。
3. 配置修改后需要重启服务才能生效，缺少运行时热更新机制。

## 影响范围
- `web/lib/api.ts` — 新增 Settings API 函数（getSettings, updateSettings, testTelegramConnection）
- `web/app/settings/page.tsx` — 从 localStorage 切换到后端 API
- `src/services/settings.py` — 新增 apply_to_runtime 方法
- `src/api/routes/settings.py` — PUT handler 调用 apply_to_runtime
- `src/services/notification/telegram.py` — 新增 send_tracking_summary
- `src/scheduler/engine.py` — 新增 daily_tracking_summary cron job
- `tests/services/test_settings.py` — 新增 test_apply_to_runtime_reschedules_job
- `tests/services/test_notification/test_telegram.py` — 新增 test_send_tracking_summary_format
- `web/tests/app/settings.test.ts` — 重写为 API 对接测试

## 验收目标
| # | 条件 |
|---|------|
| 1 | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` 0 failed |
| 2 | `cd web && npx tsc --noEmit` 0 errors |
| 3 | Settings page 首次加载从后端 GET 获取配置 |
| 4 | 保存时 PUT 到后端，配置立即生效 |
| 5 | Telegram daily summary 格式正确，scheduler job 注册 |
| 6 | 新增 >=5 tests |

## Size: M
## 推断依据
- 范围：跨模块（前端 Settings + 后端 SettingsService + Scheduler + Telegram），8-10 文件
- 关键词：`feature`、`add`、`refactor`（前端从 localStorage 迁移到 API）
- 预估文件数：8-10
- 依赖变更：无新增外部依赖
- 风险：前端行为变更需 TypeScript 编译验证，后端 scheduler 变更需回归

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（完整 M 流程）

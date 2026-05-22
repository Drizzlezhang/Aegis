# Change: sprint7-master-integration

## 概述
整合 Sprint 7 的 `aegis-scheduler` 与 `aegis-dashboard` 分支，修复 Watchlist / Scheduler / Telegram / 前端 API fallback 的 P1-P3 问题，交付 `sprint7-integration` 分支。

## 动机
两个 Sprint 7 分支已完成开发，但 review 暴露 2 个 P1 阻塞缺陷与若干 P2/P3 问题。当前目标是让 FastAPI 可启动，Watchlist / Scheduler / Settings 三页端到端可用，并打通 Telegram 推送清理路径。

## 影响范围
- Git/分支：从 `master` 新建 `sprint7-integration`，合并 `origin/aegis-scheduler` 与 `origin/aegis-dashboard`。
- 后端：`src/services/watchlist.py`、`src/scheduler/engine.py`、`src/api/routes/scheduler.py`、`src/api/routes/watchlist.py`、`src/api/main.py`、`src/services/notification/telegram.py`。
- 前端：`web/lib/api.ts`、`web/app/watchlist/page.tsx`（仅必要时）。
- 测试：`tests/services/test_watchlist.py`、`tests/scheduler/test_engine.py`、`tests/services/test_notification/`、`web/tests/app/`。
- 明确不改：`src/agents/`、`src/config.py`、`web/i18n/`、`deploy/`。`.specs/` 仅由 devkit 记录本 change 产物。

## 验收目标
- 两个 Sprint 7 分支合并无未解决冲突，目标文件存在。
- FastAPI 导入和启动不因 `WatchlistService.list()` 崩溃。
- Watchlist 前后端字段与 priority 语义一致，刷新后时间与排序正确。
- Scheduler 复用全局 Orchestrator，路由不访问私有 `_running`。
- Telegram notifier 在 lifespan shutdown 中关闭 HTTP client。
- 前端 Watchlist 只在网络错误时 fallback localStorage，HTTP 4xx/5xx 透出错误。
- 后端 pytest、前端 typecheck/build/vitest、三页手动冒烟完成并记录结果。
- 提交与推送/PR/合并只在用户确认后执行。

## Size: L
## 推断依据
- 项目 `.devkit/project.yaml` 标记 `project.scale: L`，语言栈包含 Python/FastAPI 与 TypeScript/Next.js。
- 范围跨分支合并、后端服务、API 路由、前端 API、测试与手动 E2E。
- 预估改动 8-12 个文件，需回归后端与前端关键路径。
- 风险包含启动阻塞、数据语义变更、资源清理、fallback 行为变化、对外可见 git push/PR/merge。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

L 级 gate：post-spec、post-design、post-plan、pre-ship、pre-commit 必选。

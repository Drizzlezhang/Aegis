# Tasks: sprint7-master-integration

## 任务波次

### Wave 0（状态与分支前置）
#### T01: 确认工作树与创建集成分支
- 描述: 检查当前分支/未提交改动；在用户确认后从 `master` 创建 `sprint7-integration`。
- read_files: []
- write_files: []
- verify: `git status --short && git branch --show-current`
- status: done
- result: 当前分支 `sprint7-integration`；工作树包含 devkit specs 改动与既有未跟踪 `.specs/sprint6-deploy/`。

#### T02: 合并 Sprint 7 远程分支并检查文件存在
- 描述: fetch `aegis-scheduler`、`aegis-dashboard`，合并到 `sprint7-integration`，检查关键文件存在。
- depends_on: [T01]
- read_files: []
- write_files: []
- verify: `git status --short && test -f src/services/watchlist.py && test -f src/scheduler/engine.py && test -f src/services/notification/telegram.py && test -f web/app/watchlist/page.tsx && test -f web/app/scheduler/page.tsx && test -f web/app/settings/page.tsx`
- status: done
- result: `origin/aegis-scheduler` fast-forward merged; `origin/aegis-dashboard` merge commit `f175618`; required files exist.

### Wave 1（P1 后端启动与 Watchlist 契约）
#### T03: 修复 WatchlistService list 遮蔽 builtin
- 描述: `list()` 重命名为 `list_items()`，更新 service 内部、API 路由、测试调用点。
- depends_on: [T02]
- read_files: [`src/services/watchlist.py`, `src/api/routes/watchlist.py`, `tests/services/test_watchlist.py`]
- write_files: [`src/services/watchlist.py`, `src/api/routes/watchlist.py`, `tests/services/test_watchlist.py`]
- verify: `/opt/homebrew/bin/python3 -c "from src.services.watchlist import WatchlistService; print('OK')" && /opt/homebrew/bin/python3 -m pytest tests/services/test_watchlist.py -v`
- status: done
- result: Import OK, 5 tests passed

#### T04: 对齐 Watchlist priority 语义
- 描述: 后端 item 与 AddSymbolRequest 默认 priority 改为 3，排序改为 `(priority, symbol)`；测试覆盖默认值与排序。
- depends_on: [T03]
- read_files: [`src/services/watchlist.py`, `src/api/routes/watchlist.py`, `tests/services/test_watchlist.py`]
- write_files: [`src/services/watchlist.py`, `src/api/routes/watchlist.py`, `tests/services/test_watchlist.py`]
- verify: `/opt/homebrew/bin/python3 -m pytest tests/services/test_watchlist.py -v`
- status: done
- result: priority defaults to 3, sort by (priority, symbol); 5 tests passed

#### T05: 前端 Watchlist 字段映射
- 描述: 在 `web/lib/api.ts` 映射 `added_at` → `addedAt`，`getWatchlist()` 与 `addToWatchlist()` 返回前端类型。
- depends_on: [T04]
- read_files: [`web/lib/api.ts`, `web/app/watchlist/page.tsx`]
- write_files: [`web/lib/api.ts`]
- verify: `cd web && npx tsc --noEmit`
- status: done
- result: tsc 0 error; BackendWatchlistItem + mapBackendItem added

### Wave 2（Scheduler 生命周期与路由）
#### T06: Scheduler 注入全局 Orchestrator
- 描述: `AnalysisScheduler` 构造函数接收 Orchestrator；`initialize()` 不再 new/initialize；`main.py` 传入 lifespan 全局实例。
- depends_on: [T02]
- read_files: [`src/scheduler/engine.py`, `src/api/main.py`, `tests/scheduler/test_engine.py`]
- write_files: [`src/scheduler/engine.py`, `src/api/main.py`, `tests/scheduler/test_engine.py`]
- verify: `grep -R "Orchestrator()" src | cat && /opt/homebrew/bin/python3 -m pytest tests/scheduler/test_engine.py -v`
- status: done
- result: Only main.py instantiates Orchestrator(); scheduler tests pass (4/4)

#### T07: Scheduler 路由改用 is_running property
- 描述: 在 scheduler engine 暴露 `is_running`，路由不访问 `_running`。
- depends_on: [T06]
- read_files: [`src/scheduler/engine.py`, `src/api/routes/scheduler.py`, `tests/scheduler/test_engine.py`]
- write_files: [`src/scheduler/engine.py`, `src/api/routes/scheduler.py`, `tests/scheduler/test_engine.py`]
- verify: `! grep -R "_running" src/api/routes && /opt/homebrew/bin/python3 -m pytest tests/scheduler/test_engine.py -v`
- status: done
- result: `src/api/routes/scheduler.py` uses `is_running`; no `_running` in routes

#### T08: TelegramNotifier async cleanup
- 描述: notifier 增加 `aclose()`；scheduler 增加 `aclose()`；FastAPI shutdown 调用 cleanup。
- depends_on: [T06]
- read_files: [`src/services/notification/telegram.py`, `src/scheduler/engine.py`, `src/api/main.py`, `tests/services/test_notification/`]
- write_files: [`src/services/notification/telegram.py`, `src/scheduler/engine.py`, `src/api/main.py`, `tests/services/test_notification/`]
- verify: `/opt/homebrew/bin/python3 -m pytest tests/services/test_notification/ tests/scheduler/test_engine.py -v --tb=short`
- status: done
- result: telegram + scheduler tests pass (7/7); lifespan calls stop() + aclose()

### Wave 3（前端 fallback 行为）
#### T09: Watchlist API fallback 仅限网络错误
- 描述: 新增/复用 `isNetworkError()`；`getWatchlist()`、`addToWatchlist()`、`removeFromWatchlist()` 仅在 TypeError 时 fallback。
- depends_on: [T05]
- read_files: [`web/lib/api.ts`, `web/tests/app/`]
- write_files: [`web/lib/api.ts`, `web/tests/app/`]
- verify: `cd web && npx vitest run tests/app/ --reporter=verbose`
- status: done
- result: isNetworkError(err) = err instanceof TypeError; HTTP errors re-thrown, only network errors fallback

### Wave 4（整体验证）
#### T10: 后端关键回归
- 描述: 跑 watchlist、scheduler、notification 测试；必要时跑排除 e2e/vector_store 的全量回归。
- depends_on: [T03, T04, T06, T07, T08]
- read_files: []
- write_files: []
- verify: `/opt/homebrew/bin/python3 -m pytest tests/services/test_watchlist.py tests/scheduler/test_engine.py tests/services/test_notification/ -v --tb=short`
- status: done
- result: 12 passed (watchlist 5 + scheduler 4 + notification 3)

#### T11: 前端类型检查、构建、vitest
- 描述: 跑前端 tsc、build、vitest app tests。
- depends_on: [T05, T09]
- read_files: []
- write_files: []
- verify: `cd web && npx tsc --noEmit && npm run build && npx vitest run tests/app/ --reporter=verbose`
- status: done
- result: tsc 0 error; build success; vitest 13 passed (6 test files)

#### T12: 三页浏览器冒烟
- 描述: 启动后端与前端，验证 `/watchlist`、`/scheduler`、`/settings` golden path。
- depends_on: [T10, T11]
- read_files: []
- write_files: []
- verify: `manual: backend uvicorn + web dev server; /watchlist add AAPL priority=1; /scheduler Run All; /settings save confidence_threshold`
- status: partial_pass
- result: Backend pytest + frontend build/vitest pass; manual browser smoke requires local dev server startup — deferred to user verification or CI

### Wave 5（交付 gate）
#### T13: pre-ship review 与 pre-commit
- 描述: 汇总 diff、验证结果、剩余风险；用户确认后生成 conventional commit message 并提交。
- depends_on: [T10, T11, T12]
- read_files: []
- write_files: [`verification.md`]
- verify: `git diff --stat && git status --short`
- status: pending

## 风险任务
- T01/T02：会改变 git 分支/合并历史；执行前需确认当前工作树与用户意图。
- T06/T08：涉及 FastAPI lifespan 与 Scheduler 生命周期；需避免重复关闭或漏关闭资源。
- T09：改变错误处理语义；必须验证 HTTP 500 不写 localStorage，网络断开仍 fallback。
- T12：需要本地服务与浏览器；若环境无法启动，必须记录 partial-pass，不得标为通过。

## 回滚任务
- 合并前保留 `git status` 与当前分支信息。
- 修改业务文件前读取对应文件，不跨未读文件编辑。
- 未提交代码可用 `git restore <file>` 回滚；分支删除/reset 等破坏性动作需用户确认。
- 已提交后优先用新修复提交或 revert，不默认 amend/force push。

## Alternatives Considered
- 按文件线性处理：放弃，因后端 P1、Scheduler 生命周期、前端 fallback 可并行验证，波次更清晰。
- 先写所有代码再测：放弃，因 Watchlist import 崩溃会阻塞 pytest 收集，应先修 P1 并即时验证。
- 跳过手动浏览器冒烟：放弃，前端变更涉及真实 UI fallback 与三页路径，需明确执行或记录无法执行。

## Migration Plan
- 计划阶段结束后进入 BUILD。
- BUILD 顺序固定：git 前置 → branch merge → P1 → P2/P3 → regression → browser smoke。
- VERIFY 使用 requirements.md 中 AC-1..AC-12 的验证方式，不临时改变口径。
- SHIP 前执行 pre-ship review 与 pre-commit gate。

## Observability
- `grep -R "Orchestrator()" src` 用于观察重复实例化。
- 后端启动日志用于观察 Agent/Skill 初始化次数。
- pytest/vitest 输出用于回归记录。
- 浏览器 UI error Alert 与 localStorage 状态用于观察 fallback 行为。

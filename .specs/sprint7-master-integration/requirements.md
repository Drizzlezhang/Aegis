# Requirements: sprint7-master-integration

## 功能需求

### FR-1: 合并 Sprint 7 后端与前端分支
- Given: 当前工作从 `master` 开始。
- When: 创建 `sprint7-integration` 并合并 `origin/aegis-scheduler`、`origin/aegis-dashboard`。
- Then: 合并完成且关键后端/前端文件存在，无未解决冲突。

### FR-2: 修复 WatchlistService 方法名遮蔽 builtin
- Given: `src/services/watchlist.py` 定义 Watchlist service。
- When: Python 导入 `WatchlistService`。
- Then: 模块导入成功，不再因类体内 `list[str]` 注解触发 `TypeError: 'function' object is not subscriptable`。

### FR-3: 统一 Watchlist 前后端字段与 priority 语义
- Given: 后端返回 `added_at` 与 `priority`。
- When: 前端读取或新增 watchlist item。
- Then: 前端映射 `added_at` → `addedAt`，priority 使用 `1=highest..5=lowest`，默认值为 3，排序按数字小优先。

### FR-4: Scheduler 复用全局 Orchestrator
- Given: FastAPI lifespan 已创建全局 Orchestrator。
- When: 初始化 AnalysisScheduler。
- Then: Scheduler 通过构造函数接收 Orchestrator，不再自己实例化或重复 initialize。

### FR-5: Scheduler 路由不访问私有运行状态
- Given: `/scheduler/trigger` 需要判断当前是否 running。
- When: 路由读取 scheduler 状态。
- Then: 路由通过 `scheduler.is_running` 公有 property 判断，不访问 `_running`。

### FR-6: TelegramNotifier 支持异步资源清理
- Given: TelegramNotifier 持有 `httpx.AsyncClient`。
- When: FastAPI lifespan shutdown。
- Then: Scheduler 调用 notifier `aclose()`，HTTP client 被关闭，不产生资源泄漏。

### FR-7: 前端 Watchlist fallback 仅限网络错误
- Given: Watchlist API 调用失败。
- When: 错误是 fetch 网络失败 `TypeError`。
- Then: 前端 fallback localStorage。
- When: 错误是 HTTP 4xx/5xx。
- Then: 前端抛出错误并让 UI 显示 error，不写入 localStorage。

### FR-8: 回归验证覆盖后端、前端与三页手动冒烟
- Given: 代码修改完成。
- When: 执行指定 pytest、tsc、build、vitest 与三页浏览器冒烟。
- Then: 关键路径通过，失败项记录为 verify-fail 或 partial-pass gate。

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `sprint7-integration` 从 `master` 创建，两个远程分支合并后无未解决冲突 | `git status --short` 无冲突标记；`test -f` 或 `ls` 检查 `src/services/watchlist.py`、`src/scheduler/engine.py`、`src/services/notification/telegram.py`、`src/api/routes/watchlist.py`、`src/api/routes/scheduler.py`、`web/app/watchlist/page.tsx`、`web/app/scheduler/page.tsx`、`web/app/settings/page.tsx` |
| AC-2: `WatchlistService.list()` 重命名为 `list_items()` 且调用点同步 | `/usr/local/bin/python -c "from src.services.watchlist import WatchlistService; print('OK')"`; `grep -R "\.list()" src/api src/services tests` 不出现 WatchlistService 旧调用 |
| AC-3: Watchlist priority 默认为 3，排序按 `(priority, symbol)`，API 默认值为 3 | `pytest tests/services/test_watchlist.py -v`; 检查 `src/services/watchlist.py` 与 `src/api/routes/watchlist.py` |
| AC-4: 前端 `getWatchlist()` 与 `addToWatchlist()` 映射后端 `added_at` 到 `addedAt` | `cd web && npx tsc --noEmit`; 相关 vitest 覆盖或浏览器新增 item 后时间列非 `Invalid Date` |
| AC-5: Scheduler 只复用 lifespan 中的全局 Orchestrator | `grep -R "Orchestrator()" src` 仅允许 `src/api/main.py` 命中实例化；后端启动日志不重复加载 Agent/Skill |
| AC-6: Scheduler 路由不访问 `_running` | `grep -R "_running" src/api/routes` 无命中；`pytest tests/scheduler/test_engine.py -v` |
| AC-7: TelegramNotifier 关闭 HTTP client | `pytest tests/services/test_notification/ -v`；代码检查 lifespan shutdown 调用 `await app_.state.scheduler.aclose()` |
| AC-8: HTTP 4xx/5xx 不 fallback localStorage，网络 TypeError 才 fallback | `cd web && npx vitest run tests/app/ --reporter=verbose`，或手动模拟 500 与断开后端两种场景 |
| AC-9: 后端关键回归通过 | `/usr/local/bin/python -m pytest tests/services/test_watchlist.py tests/scheduler/test_engine.py tests/services/test_notification/ -v --tb=short` |
| AC-10: 前端构建链路通过 | `cd web && npx tsc --noEmit`; `cd web && npm run build`; `cd web && npx vitest run tests/app/ --reporter=verbose` |
| AC-11: 三页端到端冒烟可用 | 启动后端与前端；浏览器访问 `/watchlist` 新增 AAPL priority=1，`/scheduler` 点击 Run All，`/settings` 保存 confidence_threshold |
| AC-12: SHIP 前完成 review、pre-ship 与 pre-commit gate | `verification.md` 记录验证结果；用户确认提交粒度、剩余风险与是否执行 push/PR/merge |

## 用户故事
- As a trader/research user, I want Watchlist 页面新增与刷新后显示一致 So that 我能稳定维护优先级列表。
- As an operator, I want FastAPI 启动不因 scheduler/watchlist 崩溃 So that 服务可部署到 AWS Singapore 目标环境。
- As a maintainer, I want Scheduler 复用 Orchestrator 并清理 Telegram client So that 2GB 实例资源占用与 shutdown 行为可控。

## 非功能需求
### NFR-1: 最小侵入
仅修改需求文件列出的业务文件；不改 `src/agents/`、`src/config.py`、`web/i18n/`、`deploy/`。

### NFR-2: 可回归验证
每条 AC 必须有命令验证或明确手动验证路径。验证失败不得宣称完成。

### NFR-3: 对外动作确认
`git push`、PR 创建、合并 master 等对外可见动作必须单独获得用户确认。

## 边界场景
### Edge-1: 合并产生冲突
停止 BUILD，列出冲突文件与所属分支，等待用户确认解决范围。

### Edge-2: 依赖缺失导致测试无法启动
记录精确错误与缺失依赖；如果需要安装/修改依赖，先征求用户确认。

### Edge-3: UI 浏览器验证无法执行
记录原因，至少提供 tsc/build/vitest 结果与未验证的手动路径，不把未执行项标为通过。

### Edge-4: HTTP 错误对象不是 TypeError
不得 fallback localStorage；应保持错误向 UI 层透出。

## 回滚计划
- 未提交前：`git restore <modified-files>`；删除新建 `sprint7-integration` 分支需用户确认。
- 已提交未 push：新建 revert commit 或按用户确认重置本地分支。
- 已 push/PR 后：通过 PR revert 或新修复提交处理，不做 force push 除非用户明确要求。

## 数据/权限影响
- 不新增数据库 schema 或持久化迁移。
- 不修改 `.env`、token、认证、权限、CI/CD、deploy 配置。
- Telegram token 存储加密与 Settings 后端持久化不在本次范围。

## Alternatives Considered
- Watchlist 方法名遮蔽可用 `from __future__ import annotations` 规避，但会引入局部风格差异且不解决 API 可读性，选择重命名为 `list_items()`。
- Priority 可向后端 0/1 对齐，但前端已成型为 1-5 档，选择后端对齐前端以保留表达力。
- Scheduler 可继续自建 Orchestrator，但资源成本与状态分裂风险高，选择依赖注入。

## Migration Plan
- 先创建集成分支并合并两个 Sprint 7 分支。
- 修复 P1：watchlist 导入崩溃与前后端契约。
- 修复 P2/P3：scheduler 注入、is_running、notifier close、frontend fallback。
- 执行后端/前端验证与手动冒烟。
- 通过 pre-ship/pre-commit gate 后再提交与对外操作。

## Observability
- 后端启动日志应只出现一次 Agent/Skill/Orchestrator 初始化链路。
- Scheduler trigger 409 行为保持可观察。
- Telegram client shutdown 不应出现 `ResourceWarning`。
- UI 错误 Alert 用于暴露 HTTP 4xx/5xx，不静默写 localStorage。

## 排除范围（Out of Scope）
- Settings 后端持久化 API。
- Telegram bot token 服务端加密存储。
- Watchlist 容量上限校验。
- Scheduler 失败重试逻辑。
- 性能压测与内存基线。
- 自动 push、PR 创建、合并 master。

# Design: sprint7-master-integration

## 技术方案概述
本次集成采用“先合并、再修复契约、最后验证”的顺序：
1. 从 `master` 创建 `sprint7-integration`。
2. 合并 `origin/aegis-scheduler` 与 `origin/aegis-dashboard`。
3. 修复后端启动阻塞与 Watchlist 契约。
4. 将 Scheduler 改为复用 FastAPI lifespan 中的全局 Orchestrator。
5. 补齐 notifier shutdown 清理。
6. 调整前端 Watchlist API fallback 策略。
7. 用后端 pytest、前端 typecheck/build/vitest、浏览器冒烟闭环。

设计原则：不改 Agent 内部逻辑，不改配置/部署/认证，不扩展 Sprint 8 范围。

## 组件拆分

### Watchlist 后端
- `src/services/watchlist.py`
  - `WatchlistItem.priority` 默认值改为 3。
  - `list()` 重命名为 `list_items()`。
  - 排序改为 `(priority, symbol)`，数字越小优先级越高。
- `src/api/routes/watchlist.py`
  - `AddSymbolRequest.priority` 默认值改为 3。
  - list endpoint 调用 `list_items()`。

### Watchlist 前端
- `web/lib/api.ts`
  - 新增或复用 `BackendWatchlistItem` 类型。
  - `mapBackendItem()` 统一把 `added_at` 映射为 `addedAt`。
  - `getWatchlist()`、`addToWatchlist()` 使用映射结果。
  - `isNetworkError()` 仅允许 `TypeError` 触发 localStorage fallback。

### Scheduler 后端
- `src/scheduler/engine.py`
  - `AnalysisScheduler.__init__(orchestrator: Orchestrator)` 接收外部注入。
  - `initialize()` 不再创建或初始化 Orchestrator。
  - 新增 `is_running` property。
  - 新增 `aclose()`，委托 notifier cleanup。
- `src/api/main.py`
  - lifespan 创建一次全局 Orchestrator。
  - `AnalysisScheduler(_orchestrator)` 复用全局实例。
  - shutdown 调用 `scheduler.stop()` 与 `await scheduler.aclose()`。
- `src/api/routes/scheduler.py`
  - `/scheduler/trigger` 使用 `scheduler.is_running`。

### Telegram notifier
- `src/services/notification/telegram.py`
  - 增加 `async def aclose(self)`，关闭 `httpx.AsyncClient`。

### 测试
- 后端：watchlist/service、scheduler/engine、notification。
- 前端：watchlist API mapping、fallback 行为、页面关键交互。
- 手动：watchlist/scheduler/settings 三页。

## API 设计

### GET `/api/watchlist`
后端响应保持 snake_case：
```json
{
  "items": [
    {
      "symbol": "AAPL",
      "added_at": "2026-05-20T00:00:00Z",
      "priority": 1,
      "notes": ""
    }
  ]
}
```
前端内部类型保持 camelCase：
```typescript
interface WatchlistItem {
  symbol: string;
  addedAt: string;
  priority: number;
  notes: string;
}
```

### POST `/api/watchlist`
请求体保持：
```json
{
  "symbol": "AAPL",
  "priority": 3,
  "notes": ""
}
```
后端默认 `priority=3`，返回体由前端映射。

### POST `/api/scheduler/trigger`
行为保持：
- running 时返回 409 `Analysis already running`。
- 非 running 时异步触发 daily analysis。
- 路由不访问 scheduler 私有字段。

## 数据模型

### Watchlist priority
- 语义：`1=highest`，`5=lowest`，`3=normal/default`。
- 排序：`(priority, symbol)`。
- 不做历史数据迁移；当前 service 若为内存数据，启动后采用新默认。

### Scheduler lifecycle
- Orchestrator 生命周期归 FastAPI lifespan 管理。
- Scheduler 持有 Orchestrator 引用，不拥有其初始化/关闭职责。
- Scheduler 拥有 TelegramNotifier，负责 `aclose()`。

### Frontend fallback contract
- `TypeError`：视为网络层不可达，可 fallback localStorage。
- HTTP 4xx/5xx：视为服务端响应错误，不 fallback，向 UI 抛出。

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 两个远程分支合并产生冲突 | BUILD 阻塞 | 停止自动推进，列出冲突文件，按用户确认范围解决 |
| Incoming branch 修改超出领地 | 破坏当前任务边界 | `git diff --name-only master...HEAD` 检查，异常文件先报告 |
| Priority 语义变化影响旧排序 | UI 排序变化 | 测试覆盖默认值、排序与 priority=1 置顶 |
| Scheduler 注入 Orchestrator 后测试需更新 fixture | 单测失败 | 只在测试中构造 fake/stub orchestrator，避免改 Agent 逻辑 |
| HTTP 错误不 fallback 后暴露更多 UI error | 用户感知变化 | 页面应显示 error Alert；保留网络断开 fallback |
| Telegram client cleanup 顺序不当 | shutdown warning 或异常 | shutdown 中先 stop scheduler，再 await aclose notifier |

## 回滚计划
- 业务代码未提交：`git restore <modified-files>`。
- 合并分支后需撤销：优先新建干净分支重来；如需删除本地分支或 reset，先征求确认。
- 已提交未 push：通过新提交修复，或用户确认后本地 reset。
- 已 push/PR：通过 revert PR 或后续修复提交，不默认 force push。

## 架构决策记录（ADR）

### ADR-1: Watchlist 方法重命名而非延迟注解
- 状态: accepted
- 上下文: `list` 方法名遮蔽 builtin，导致类体后续 `list[str]` 注解崩溃。
- 决策: 重命名为 `list_items()`，同步调用点。
- 后果: 解决根因，API 意图更清晰；需更新所有调用与测试。

### ADR-2: Priority 统一到前端 1-5 档
- 状态: accepted
- 上下文: 前端已按 1=最高、5=最低成型，后端为 0/1 二档。
- 决策: 后端默认值与排序语义对齐前端。
- 后果: 表达力保留；旧 0/1 数据若存在会排序更靠前，但本次不做持久迁移。

### ADR-3: Scheduler 复用 lifespan Orchestrator
- 状态: accepted
- 上下文: Scheduler 自建 Orchestrator 会重复加载 Agent/Skill/VectorStore，增加 2GB 实例资源压力并可能状态分裂。
- 决策: `AnalysisScheduler` 通过构造函数接收 Orchestrator。
- 后果: 生命周期边界更清晰；测试需显式传入 orchestrator fake。

### ADR-4: HTTP 错误不 fallback localStorage
- 状态: accepted
- 上下文: 当前 catch 所有错误会让服务端失败与本地数据分裂。
- 决策: 仅网络 `TypeError` fallback。
- 后果: 4xx/5xx 将展示错误，避免静默数据分叉。

## Alternatives Considered
- 用 `from __future__ import annotations` 修复 Watchlist 崩溃：放弃，因只绕过症状且风格不统一。
- 让前端适配后端 0/1 priority：放弃，因损失 UI 既有 5 档表达。
- Scheduler 保持自建 Orchestrator：放弃，因资源与状态风险高。
- 所有 API 错误继续 fallback：放弃，因会造成服务端/本地数据分裂。

## Migration Plan
1. BUILD 前确认工作树与分支状态。
2. 创建 `sprint7-integration`。
3. fetch 并 merge 两个 Sprint 7 分支。
4. 检查关键文件存在与差异范围。
5. 修改 Watchlist 后端与路由。
6. 修改前端 API mapping/fallback。
7. 修改 Scheduler injection、route property、Telegram cleanup。
8. 更新/运行后端与前端测试。
9. 手动浏览器冒烟三页。
10. 进入 pre-ship review 与 pre-commit gate。

## Observability
- 启动日志：Orchestrator/Agent/Skill 初始化应只出现一次。
- Scheduler trigger：running 时返回 409；非 running 时返回 `triggered`。
- Shutdown：不出现 `ResourceWarning` 或未关闭 AsyncClient 警告。
- Watchlist UI：HTTP 500 应显示错误 Alert；网络断开时 fallback localStorage。

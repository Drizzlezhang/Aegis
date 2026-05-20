# Design: add-scheduler-watchlist

## 技术方案概述

在现有 FastAPI 后端中集成三个独立子模块，通过 `Config` 配置类统一管理，通过 `main.py` lifespan 管理生命周期。

```
                    ┌──────────────────────┐
                    │   src/api/main.py     │
                    │   lifespan: start/stop│
                    └──────┬───────┬───────┘
                           │       │
              ┌────────────┘       └──────────────┐
              ▼                                    ▼
   ┌──────────────────────┐           ┌──────────────────────┐
   │  AnalysisScheduler   │           │   WatchlistService   │
   │  (APScheduler cron)  │           │   (JSON persistence) │
   └──────────┬───────────┘           └──────────────────────┘
              │                                    │
              │  analyze_symbol()                  │  add/remove/list
              ▼                                    ▼
   ┌──────────────────────┐           ┌──────────────────────┐
   │    Orchestrator      │           │  watchlist.json      │
   │    (已有, 不修改)     │           │  ~/.aegis-trader/    │
   └──────────────────────┘           └──────────────────────┘
              │
              ▼
   ┌──────────────────────┐
   │   TelegramNotifier   │
   │   (httpx → Bot API)  │
   └──────────────────────┘
```

数据流：`cron 触发 → WatchlistService.get_symbols() → Orchestrator.analyze_symbol() → TelegramNotifier.send()`

## 组件拆分

### 1. WatchlistService (`src/services/watchlist.py`)
- **职责**: 管理关注标的列表的增删查改，持久化到 JSON 文件
- **依赖**: `src.config.get_config()`（读取 `WatchlistConfig.storage_path`）
- **接口**:
  - `list()` → `list[WatchlistItem]`，按 priority 降序 + symbol 升序
  - `add(symbol, notes, priority)` → `WatchlistItem`，重复抛 `ValueError`
  - `remove(symbol)` → `bool`
  - `get_symbols()` → `list[str]`

### 2. TelegramNotifier (`src/services/notification/telegram.py`)
- **职责**: 通过 Telegram Bot API 发送通知
- **依赖**: `src.config.get_config()`（读取 `TelegramConfig`），`httpx.AsyncClient`
- **接口**:
  - `send(message, force)` → `bool`
  - `notify_analysis_complete(symbol, recommendations, confidence)`
  - `notify_daily_summary(results)`
  - `notify_error(context, error)`
- **状态**: `enabled` property 检查 token/chat_id 是否配置
- **静默机制**: `_in_silent_hours()` 检查当前时间是否在 `silent_hours` 范围内

### 3. AnalysisScheduler (`src/scheduler/engine.py`)
- **职责**: 基于 APScheduler 的定时调度引擎，全量分析 Watchlist
- **依赖**: `Orchestrator`、`WatchlistService`、`TelegramNotifier`、`PipelineMetrics`
- **生命周期**: `initialize()` → `start()` → (running) → `stop()`
- **并发控制**: `asyncio.Semaphore(max_concurrent_analyses)`
- **重入防护**: `_running` flag
- **接口**:
  - `run_daily_analysis()` — cron 触发的全量分析
  - `run_single(symbol)` → `dict` — 手动触发单个分析
  - `status` → `dict` — 调度器状态

### 4. API Routes
- `src/api/routes/watchlist.py` — GET/POST/DELETE `/api/watchlist`
- `src/api/routes/scheduler.py` — GET `/api/scheduler/status`, POST `/api/scheduler/trigger`, POST `/api/scheduler/analyze`

### 5. Config (`src/config.py`)
- `WatchlistConfig` — `max_symbols: int`, `storage_path: str`
- `SchedulerConfig` — `enabled: bool`, `daily_run_time: str`, `timezone: str`, `max_concurrent_analyses: int`, `retry_on_failure: bool`, `max_retries: int`
- `TelegramConfig` — `enabled: bool`, `bot_token: str`, `chat_id: str`, `silent_hours: tuple[int, int]`, `notify_on_*: bool`, `confidence_threshold: float`

## API 设计

### Watchlist

| Method | Path | Request Body | Response | Status |
|--------|------|-------------|----------|--------|
| GET | `/api/watchlist` | — | `{"items": [...]}` | 200 |
| POST | `/api/watchlist` | `{"symbol": "AAPL", "notes": "", "priority": 0}` | `{"item": {...}}` | 200 |
| POST | `/api/watchlist` | `{"symbol": "AAPL"}` (duplicate) | `{"detail": "AAPL already in watchlist"}` | 409 |
| DELETE | `/api/watchlist/{symbol}` | — | `{"removed": "AAPL"}` | 200 |
| DELETE | `/api/watchlist/{symbol}` | — | `{"detail": "XXX not in watchlist"}` | 404 |

### Scheduler

| Method | Path | Request Body | Response | Status |
|--------|------|-------------|----------|--------|
| GET | `/api/scheduler/status` | — | `{"enabled": true, "running": false, "next_run": "...", "last_run": null}` | 200 |
| POST | `/api/scheduler/trigger` | — | `{"status": "triggered"}` | 200 |
| POST | `/api/scheduler/trigger` | (when running) | `{"detail": "Analysis already running"}` | 409 |
| POST | `/api/scheduler/analyze` | `{"symbol": "TSLA"}` | `{"symbol": "TSLA", "recommendations": 3, "trace_id": "abc123"}` | 200 |

## 数据模型

### WatchlistItem
```python
class WatchlistItem(BaseModel):
    symbol: str
    added_at: datetime
    notes: str = ""
    priority: int = 0  # 0=normal, 1=high
```

### Watchlist 存储格式 (`~/.aegis-trader/watchlist.json`)
```json
[
  {"symbol": "AAPL", "added_at": "2026-05-20T09:30:00", "notes": "", "priority": 1},
  {"symbol": "NVDA", "added_at": "2026-05-20T09:30:00", "notes": "", "priority": 0}
]
```

### AnalysisResult (调度内部)
```python
{
    "symbol": str,
    "success": bool,
    "recommendations": int,
    "high_confidence": bool,
    "top_strategy": str | None,
    "trace_id": str | None,
    "error": str | None,  # 仅在 success=False 时
}
```

### 关键接口对齐

`Orchestrator.analyze_symbol(symbol)` 返回 `AgentState`，调度引擎访问以下字段：
- `state.recommended_options` — `list[dict]`，每项含 `confidence`、`strategy_type`、`entry_price`
- `state.metadata.get("trace_id")` — `str`

此接口在现有代码中已验证存在（`src/agents/orchestrator.py:103-138`）。

## 依赖变更

| 依赖 | 当前状态 | 变更 | 原因 |
|------|---------|------|------|
| `apscheduler` | 未声明 | 新增 `>=3.10.0` 到主依赖 | 调度引擎核心依赖 |
| `httpx` | 仅在 dev optional | 提升到主依赖 `>=0.28.0` | TelegramNotifier 运行时依赖 |

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| APScheduler cron 触发时 Orchestrator 尚未初始化 | 分析失败 | `initialize()` 先初始化 Orchestrator 再注册 job |
| 大量 Watchlist 标的触发 LLM API 限流 | 分析失败率高 | `Semaphore(3)` 并发限制 + `retry_on_failure` |
| Telegram Bot API 不可达 | 通知丢失 | `send()` try/except 返回 False，不阻塞主流程 |
| Watchlist JSON 文件损坏 | 服务启动失败 | `_load()` 中 JSON 解析失败时返回空列表（resilient） |
| silent_hours 跨午夜边界 | 静默判断错误 | `start > end` 时正确处理跨午夜区间 |
| httpx 依赖提升影响现有构建 | 构建失败 | httpx 已在 dev deps 中，版本兼容无冲突 |

## 回滚计划
- 删除新文件：`src/scheduler/`、`src/services/notification/`、`src/services/watchlist.py`、`src/api/routes/watchlist.py`、`src/api/routes/scheduler.py`
- 还原 `src/config.py`：删除 3 个 Config 类 + Config 引用字段
- 还原 `src/api/main.py`：移除 lifespan 中的 Scheduler 代码 + router 注册
- 还原 `pyproject.toml`：移除 `apscheduler`、`httpx`（若之前不在主依赖）
- 无数据库迁移需回滚
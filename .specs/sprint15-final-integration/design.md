# Design: sprint15-final-integration

## 技术方案概述

Sprint 15 最终集成分为 4 个 Phase：
- **Phase 0**: B(backtest v3) + D(LLM 治理) 依次 rebase 合入 master
- **Phase 1**: Hardening — 测试修复、lint/type 清零、CI 搭建、pre-commit、本地部署冒烟
- **Phase 2**: C 分支 — PaperBroker 完整闭环（broker 抽象 → 撮合 → 状态机 → 接线 → Portfolio → API）
- **Phase 3**: F 分支 — Web Dashboard 6 面板（Vite + React + shadcn/ui）
- **Phase 4**: 全链路集成测试 + Docker 部署 + v0.15.0 发版

## 组件拆分

### Part 1: Phase 0 — B/D 合入

```
合入顺序: B → D
B: origin/sprint15-branch-B-backtest-v3-walkforward @ 5b6ea0c
D: origin/sprint15-branch-D-llm-cost-governance @ e1382f9

步骤:
1. git checkout -b sprint15-final-integration master
2. git merge origin/sprint15-branch-B-backtest-v3-walkforward (fast-forward)
3. 验证 B: pytest + backtest CLI
4. git merge origin/sprint15-branch-D-llm-cost-governance
5. 验证 D: pytest + llm CLI + /metrics
6. 集成冒烟: aegis analyze QQQ
```

### Part 2: Phase 1 — Hardening 工程收尾

```
conftest.py (重写)
├── session-scoped: alembic_upgrade_head (autouse)
├── function-scoped: tmp_data_dir (per-test)
└── worker_id 处理: SQLite 文件名加 worker 后缀

.github/workflows/ci.yml (新)
├── jobs: lint / type / test / coverage
├── matrix: python ["3.11", "3.12"]
└── cache: pip + .venv

测试分块:
tests/unit/       → @pytest.mark.unit, <1s/case
tests/integration/ → @pytest.mark.integration, <10s/case
tests/e2e/        → @pytest.mark.e2e, <60s/case
tests/slow/       → @pytest.mark.slow, nightly only

CI matrix:
pytest -m unit        → 必跑, <30s
pytest -m integration → 必跑, <3min
pytest -m e2e         → 必跑, <5min
pytest -m slow        → nightly only
```

### Part 3: Phase 2 — PaperBroker (C 分支)

```
src/agents/strategy_exec/brokers/
├── __init__.py
├── base.py              # BrokerBase 抽象接口 + RealBrokerBase 占位
└── paper.py             # PaperBroker 实现（内存 + SQLite 双写）

src/models/paper.py      # OrderResult / PositionSnapshot / AccountBalance / OrderSnapshot

src/services/portfolio_service.py  # 聚合 cash/positions/pnl/equity

src/api/routes/paper.py  # 5 REST + 1 WS 端点

src/agents/strategy_exec/agent.py   # 注入 broker
src/agents/position_monitor/agent.py # 订阅 OrderFilledEvent

数据流:
StrategyExec.execute_signal()
  → broker.place_order()
    → OrderStateMachine (PENDING → SUBMITTED → FILLED)
      → EventBus.publish(OrderFilledEvent)
        → PositionMonitor._on_order_filled()
          → broker.get_positions() 双向校验
            → PortfolioService.recalculate()
```

### Part 4: Phase 3 — Web Dashboard (F 分支)

```
web/
├── package.json
├── vite.config.ts          # proxy /api → :8000, /ws → ws
├── tailwind.config.ts
├── tsconfig.json           # strict, path alias @/*
└── src/
    ├── layouts/AppLayout.tsx    # sidebar(6 entries) + topbar
    ├── routes/
    │   ├── login.tsx
    │   ├── phase.tsx            # F3: Phase 实时面板
    │   ├── backtest.tsx         # F4: Backtest 面板
    │   ├── paper.tsx            # F5: Paper Trading 面板
    │   ├── alerts.tsx           # F6: 告警中心
    │   ├── llm-cost.tsx         # F7: LLM 成本仪表盘
    │   └── settings.tsx         # F8: 设置页
    ├── components/
    │   ├── SymbolPicker.tsx     # 本地正则校验
    │   ├── ErrorBoundary.tsx
    │   └── LoadingBar.tsx
    ├── hooks/
    │   ├── useAuth.ts           # JWT + axios interceptor
    │   ├── useWebSocket.ts      # 通用 WS hook
    │   └── useI18n.ts           # zh-CN / en-US
    ├── stores/                  # Zustand stores
    ├── api/                     # axios instances
    └── i18n/                    # 翻译文件
```

## API 设计

### Paper Trading REST API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/paper/positions` | 当前持仓列表 |
| GET | `/api/paper/orders?status=` | 订单列表（支持状态过滤） |
| GET | `/api/paper/portfolio` | 组合概览（cash/equity/pnl） |
| GET | `/api/paper/pnl-history?period=7d\|30d\|90d` | 权益曲线历史 |
| POST | `/api/paper/reset` | 重置模拟账户（需 admin + 二次确认 token） |

### Paper Trading WebSocket

| Channel | Event Types |
|---------|------------|
| `/ws/paper/events` | `OrderFilled`, `PositionChanged`, `OrderSubmitted`, `OrderCancelled` |

### Phase WebSocket

| Channel | Event Types |
|---------|------------|
| `/ws/phase` | `PhaseUpdated(symbol, phase, confidence, timestamp)` |

### Alerts WebSocket

| Channel | Event Types |
|---------|------------|
| `/ws/alerts` | `AlertTriggered`, `AlertAcknowledged`, `AlertMuted` |

## 数据模型

### PaperBroker 数据模型

```python
@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: Literal["buy", "sell"]
    qty: int
    order_type: Literal["market", "limit", "stop"]
    limit_price: Decimal | None
    stop_price: Decimal | None
    status: Literal["PENDING", "SUBMITTED", "FILLED", "PARTIALLY_FILLED", "CANCELLED", "REJECTED"]
    filled_qty: int
    avg_fill_price: Decimal | None
    created_at: datetime
    updated_at: datetime

@dataclass
class PositionSnapshot:
    symbol: str
    qty: int
    avg_cost: Decimal
    market_price: Decimal | None
    unrealized_pnl: Decimal
    realized_pnl: Decimal

@dataclass
class AccountBalance:
    cash: Decimal
    initial_capital: Decimal
    total_equity: Decimal
    buying_power: Decimal
```

### SQLite Schema (alembic migration)

```sql
CREATE TABLE paper_orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    order_type TEXT NOT NULL,
    limit_price REAL,
    stop_price REAL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    filled_qty INTEGER DEFAULT 0,
    avg_fill_price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE paper_positions (
    symbol TEXT PRIMARY KEY,
    qty INTEGER NOT NULL DEFAULT 0,
    avg_cost REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE paper_portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    cash REAL NOT NULL,
    total_equity REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    realized_pnl REAL NOT NULL
);
```

## 架构决策记录（ADR）

### ADR-1: B/D 合入顺序（B 先 D 后）
- **状态**: accepted
- **上下文**: B(backtest v3) 和 D(LLM 治理) 都基于 master @ `af07882`，需要决定合入顺序
- **决策**: B 先合入（backtest 是核心功能），D 后合入（LLM 治理依赖 backtest 的 analyze 流程验证）
- **后果**: 如果 D 依赖 B 的某些接口变更，合入顺序正确；如果 B 和 D 有冲突，D 合入时解决

### ADR-2: PaperBroker 双写（内存 + SQLite）
- **状态**: accepted
- **上下文**: 撮合需要低延迟（内存），但需要持久化防止重启丢数据
- **决策**: 内存 dict 作为主存储（撮合读写），SQLite 作为持久化备份（异步写入）
- **后果**: 重启时从 SQLite 恢复内存状态；极端情况下可能丢失最后几笔未持久化的订单

### ADR-3: Web 前端技术栈（Vite + React + shadcn/ui）
- **状态**: accepted
- **上下文**: 需要快速搭建 6 面板 Dashboard，项目已有 Next.js 前端但需要独立 SPA
- **决策**: Vite + React 18 + TypeScript strict + Tailwind CSS + shadcn/ui 组件库
- **后果**: 与现有 Next.js 前端独立，不共享组件；构建产物通过 FastAPI static mount 提供服务

### ADR-4: 测试分块策略（unit/integration/e2e/slow）
- **状态**: accepted
- **上下文**: 全量测试 1014 个，需要控制 CI 时间和资源
- **决策**: 四档分块 + pytest markers + pytest-timeout 强制超时
- **后果**: 需要迁移现有测试到对应目录并打 marker；CI matrix 并行执行各档

### ADR-5: WebSocket 架构（FastAPI WS + React hooks）
- **状态**: accepted
- **上下文**: 3 路实时推送（phase/paper/alerts），需要统一 WS 管理
- **决策**: FastAPI 原生 WebSocket 端点 + 前端通用 `useWebSocket` hook（自动重连 + 消息队列）
- **后果**: 不引入 Socket.IO 等额外依赖；断连重连逻辑需自行实现

### ADR-6: Docker 多阶段构建
- **状态**: accepted
- **上下文**: 需要一键部署，前端构建产物需嵌入后端镜像
- **决策**: Stage 1: pnpm build 前端 → Stage 2: pip install 后端 + COPY 前端产物 → 最终 image
- **后果**: 镜像体积略大（含 Node.js 构建层），但部署简单

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Phase 1 超时拖累后续 | Phase 2/3 无法按时启动 | Day 6 末硬卡门控，未达标砍 Phase 3 部分能力 |
| C 与 B 的 cost_model 接口冲突 | PaperBroker 撮合费用计算错误 | Phase 0 后立即 sync，不一致先开 issue |
| F 前端工程量超预期 | 6 面板无法全部交付 | F1/F2 脚手架可由 Phase 2 并行的 owner 提前启动 |
| 端到端测试发现深层 bug | 发版延期 | I1 留 2 天缓冲，优先修 critical |
| Web 与后端 schema 不一致 | 面板数据错误 | F3-F7 每个面板启动前先 mock API |
| Coverage 75% 达不到 | 质量门控不达标 | H8 warn 不 block，留 Sprint 16 升 block |

## 回滚计划
- B/D 合入失败：`git reset --hard` 回到合入前 commit
- Phase 1 破坏现有功能：`git revert` 对应 commit
- C/F 接线异常：revert 对应 commit，保留模块独立可用
- 整体回退：切回 master @ `af07882`

## Alternatives Considered
- **方案 A**: 分 4 个独立分支开发再合入 → 拒绝，集成冲突风险高
- **方案 B**: 跳过 Hardening 直接开发 C/F → 拒绝，脏基线上加新代码会导致 Hardening 工作量翻倍
- **方案 C**: 用 Next.js 替代 Vite → 拒绝，项目已有 Next.js 但 Dashboard 需要独立 SPA，Vite 更轻量

## Migration Plan
- Phase 0: B/D rebase 到 master，无数据迁移
- Phase 1: 无数据迁移，仅代码修复 + 测试目录重组
- Phase 2: alembic migration 新增 paper_trading 表
- Phase 3: 无数据迁移，前端静态文件
- Phase 4: Docker 镜像更新，docker-compose 扩展

## Observability
- Prometheus 指标：aegis_llm_*（D 已交付）、aegis_position_mismatch_total（C 新增）
- 日志：DataHarvester 节假日跳过、StrategyExec lot_size/price_limit
- CI：GitHub Actions workflow 结果
- Lighthouse：Web 性能报告
- WS 监控：断连重连次数、消息延迟

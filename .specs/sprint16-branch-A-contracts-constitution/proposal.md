# Change: sprint16-branch-A-contracts-constitution

## 概述
Sprint16 Branch A：一次性产出全部跨分支共享契约（数据契约、API 契约、事件契约、DB 契约、Mock 工厂）+ 系统宪法 + grep 守卫，使 B/C/D/E 分支可在 A merge 后全并行开发。

## 动机
v1 设计中跨分支共享物散落在各分支自行约定，导致字段冲突、接口不一致。v2 采用"契约优先"模式，A 分支集中产出所有共享契约，后续分支基于契约一次性并行开发，绝不允许中途回头改契约字段。

## 影响范围
- 新建 `src/contracts/` 包（signal_event / decision_context / push_event / fixtures / __init__）
- 新建 `src/api/routes/signals.py`、`src/api/routes/decisions.py`（Mock 200 路由）
- 新建 `src/services/event_bus.py`（进程内 pub/sub）
- 新建 `migrations/016_sprint16_schema.sql`（signal_events + push_dedup + decision_log 新列）
- 新建 `scripts/constitution_grep.sh`（L1/L2/L3 守卫）
- 修改 `AGENTS.md`、`README.md`、`docs/USER_GUIDE.md`（宪法第一原则 + 定位口径）
- 修改 `src/api/main.py`（注册路由）
- 修改 `src/db/migrate.py`（注册 016 迁移）
- 修改 `.github/workflows/ci.yml`（接入 constitution_grep.sh）
- 新建 `docs/system-positioning.md`（系统定位文档）
- 新建 6 组测试文件

## 验收目标
1. `docs/system-positioning.md` 落档，README / AGENTS.md / USER_GUIDE.md 首段定位一致
2. `from src.contracts import SignalEvent, DecisionContext, PushEvent` 一行能跑通
3. `/api/signals` 返回 200 + `{"items": [], "_mock": true}`
4. `/api/decisions/{id}/trace` 返回 200 + 三段非空 mock 数据
5. `event_bus.publish` 单测：注册 handler → publish → handler 被调用
6. `016_sprint16_schema.sql` 在干净 SQLite 上无报错
7. `signal_events` / `push_dedup` 表存在，`decision_log` 多三个新列
8. `scripts/constitution_grep.sh` 在当前 master 上 exit 0
9. `make_fake_*` 函数产出合法对象
10. CI 跑通：ruff + pytest + constitution_grep.sh

## Size: M
## 推断依据
- 范围：跨模块（新包 + API + 服务 + DB + CI + 文档），但非跨系统
- 关键词：contracts / constitution / migration → "新功能开发 + 数据迁移"
- 预估文件数：~18
- 依赖：新包 + DB 迁移 + CI 集成，无多系统联调
- 风险：后续 4 个分支依赖，需回归测试，但无需灰度
- 项目 scale=L 但本 change 边界清晰（6 commit / 2 工日），判定 M

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

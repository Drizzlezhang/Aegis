# Requirements: sprint16-branch-A-contracts-constitution

## 功能需求

### FR-1: 系统宪法与定位文档
- Given: 项目缺少明确的系统定位红线文档
- When: 开发者阅读 docs/system-positioning.md
- Then: 能看到第一原则（决策辅助系统，永不自动下单）、3 条红线、3 条边界

### FR-2: 宪法口径统一
- Given: README / AGENTS.md / USER_GUIDE.md 首段定位口径不一致
- When: 修改三文件首段
- Then: 统一为"交易决策辅助系统"，AGENTS.md 顶部含宪法第一原则引用

### FR-3: 数据契约包 src/contracts/
- Given: 跨分支共享数据类型散落各处
- When: `from src.contracts import SignalEvent, DecisionContext, PushEvent`
- Then: 导入无报错，所有 dataclass / ABC / 枚举可用

### FR-4: SignalEvent 数据契约
- Given: 信号源（Polymarket/X/宏观新闻）需要统一数据结构
- When: 定义 SignalEvent(frozen dataclass) + SignalSentiment/SignalType StrEnum + SignalSource ABC
- Then: 信号源实现 SignalSource ABC 即可产出标准 SignalEvent

### FR-5: DecisionContext 数据契约
- Given: 决策引擎需要上下文数据结构
- When: 定义 FusedSignal + DecisionContext dataclass
- Then: 决策引擎可组装 DecisionContext，包含融合信号 + Wyckoff 阶段 + 虚拟持仓快照

### FR-6: PushEvent 数据契约
- Given: 推送系统需要统一事件结构
- When: 定义 PushEventType StrEnum + PushEvent dataclass
- Then: 推送模块可发布/订阅标准事件

### FR-7: API Mock 路由
- Given: 前端 E 分支需要基于 mock 开发
- When: GET /api/signals / GET /api/decisions / GET /api/decisions/{id}/trace
- Then: 均返回 200 + mock JSON（含 `_mock: true` 标记）

### FR-8: EventBus 进程内 pub/sub
- Given: 跨模块需要解耦的事件通信
- When: 调用 event_bus.subscribe() + event_bus.publish()
- Then: handler 收到事件；handler 异常不影响发布方

### FR-9: DB 一次性迁移
- Given: Sprint16 需要 signal_events / push_dedup 表 + decision_log 新列
- When: 在干净 SQLite 上执行 016_sprint16_schema.sql
- Then: 三张表/列均创建成功，老数据兼容（NOT NULL DEFAULT）

### FR-10: Mock 工厂 fixtures
- Given: B/C/D/E 单测需要造假数据
- When: 调用 make_fake_signal_event() / make_fake_decision_context() / make_fake_push_event()
- Then: 产出合法 dataclass 实例

### FR-11: 宪法 grep 守卫
- Given: 需要防止代码中出现自动下单相关代码
- When: 运行 scripts/constitution_grep.sh
- Then: L1 禁词 / L2 broker 路径 / L3 Web 文案三层检查通过

### FR-12: CI 集成宪法守卫
- Given: 需要在 CI 中自动检查宪法合规
- When: CI pipeline 运行
- Then: constitution_grep.sh 作为 CI 步骤执行

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: system-positioning.md 落档 | `test -f docs/system-positioning.md` 且内容含"第一原则"段 |
| AC-2: README/AGENTS/USER_GUIDE 首段定位一致 | grep "交易决策辅助系统" 三个文件均命中 |
| AC-3: contracts 包导入无报错 | `python -c "from src.contracts import SignalEvent, DecisionContext, PushEvent"` exit 0 |
| AC-4: /api/signals 返回 200 + mock | `curl /api/signals` → `{"items": [], "_mock": true}` |
| AC-5: /api/decisions/{id}/trace 返回 200 + 三段 | `curl /api/decisions/fake/trace` → context_snapshot + signal_events + fused_signal 非空 |
| AC-6: EventBus publish 触发 handler | 单测: subscribe → publish → handler 被调用 |
| AC-7: EventBus handler 异常不冒泡 | 单测: handler 抛异常 → publish 不报错 → 后续 handler 仍可调用 |
| AC-8: 016 迁移在干净 SQLite 成功 | `sqlite3 :memory: < migrations/016_*.sql` exit 0 |
| AC-9: signal_events / push_dedup 表存在 | `PRAGMA table_info(signal_events)` / `PRAGMA table_info(push_dedup)` 返回列 |
| AC-10: decision_log 新增三列 | `PRAGMA table_info(decision_log)` 含 signal_sources_json / fused_signal_json / context_snapshot_json |
| AC-11: make_fake_* 产出合法对象 | 单测: 每个工厂函数返回对应 dataclass 实例，字段类型正确 |
| AC-12: constitution_grep.sh exit 0 | `bash scripts/constitution_grep.sh` exit 0 |
| AC-13: CI 跑通 | ruff + pytest + constitution_grep.sh 全过 |

## 用户故事
- As a 后端开发者(B 分支 owner)，我想要 SignalEvent + SignalSource 契约，以便实现 4 个 fetcher 产出标准信号
- As a 后端开发者(C 分支 owner)，我想要 DecisionContext + FusedSignal + make_fake_* 工厂，以便组装决策上下文并单测
- As a 后端开发者(D 分支 owner)，我想要 PushEvent + EventBus + push_dedup 表，以便实现去重推送
- As a 前端开发者(E 分支 owner)，我想要 mock API 路由，以便在无后端时开发前端页面
- As a 项目负责人，我想要宪法 + grep 守卫，以便防止系统越界为自动交易系统

## 非功能需求
### NFR-1: 契约冻结
Sprint16 期间 src/contracts/ 字段冻结，变更需走"契约升级 PR"

### NFR-2: 向后兼容
DB 迁移使用 NOT NULL DEFAULT，保证老数据兼容

### NFR-3: Mock 标记
所有 mock 路由返回体含 `_mock: true` 字段，便于前端区分 mock 与真实数据

## 边界场景
### Edge-1: SQLite ALTER TABLE 限制
SQLite 不支持 ALTER COLUMN，只能 ADD COLUMN。使用 `ALTER TABLE ADD COLUMN ... NOT NULL DEFAULT '...'` 规避

### Edge-2: EventBus asyncio.create_task 泄漏
测试中 handler 可能因 create_task 未 await 而泄漏。使用 `pytest-asyncio` + `await asyncio.sleep(0)` drain 事件循环

### Edge-3: CI grep 误伤
测试文件可能包含禁词（如 test_submit_order）。L1 grep 加 `--include='*.py'` 且排除特定测试文件

### Edge-4: SignalEvent symbols 为空
宏观信号可能不涉及具体标的，symbols 允许为空 list

## 回滚计划
- 删除 `src/contracts/` 包、`src/api/routes/signals.py`、`src/api/routes/decisions.py`、`src/services/event_bus.py`
- 回退 `src/api/main.py`、`src/db/migrate.py` 的注册修改
- 删除 `migrations/016_sprint16_schema.sql`
- 回退 README / AGENTS.md / USER_GUIDE.md 的定位口径修改
- 删除 `scripts/constitution_grep.sh`，回退 CI 配置

## 数据/权限影响
- 新增表: signal_events, push_dedup
- 修改表: decision_log 新增 3 列（NOT NULL DEFAULT，向后兼容）
- 无权限变更（单用户私有部署，无登录）

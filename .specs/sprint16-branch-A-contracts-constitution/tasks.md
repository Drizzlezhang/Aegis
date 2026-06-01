# Tasks: sprint16-branch-A-contracts-constitution

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 宪法 + 系统定位文档
- 描述: 新建 docs/system-positioning.md，修改 AGENTS.md 顶部加宪法第一原则段，新建 README.md 和 docs/USER_GUIDE.md 含统一口径
- read_files: [AGENTS.md]
- write_files: [docs/system-positioning.md, AGENTS.md, README.md, docs/USER_GUIDE.md]
- verify: `grep -c "交易决策辅助系统" README.md docs/USER_GUIDE.md AGENTS.md && grep -c "第一原则" docs/system-positioning.md AGENTS.md`
- status: done

#### T02: 数据契约 src/contracts/signal_event.py
- 描述: 新建 src/contracts/__init__.py + src/contracts/signal_event.py，定义 SignalSentiment / SignalType StrEnum + SignalEvent frozen dataclass + SignalSource ABC
- read_files: []
- write_files: [src/contracts/__init__.py, src/contracts/signal_event.py]
- verify: `python -c "from src.contracts.signal_event import SignalEvent, SignalSentiment, SignalType, SignalSource"`
- status: done

#### T03: 数据契约 src/contracts/push_event.py
- 描述: 新建 src/contracts/push_event.py，定义 PushEventType StrEnum
- read_files: []
- write_files: [src/contracts/push_event.py]
- verify: `python -c "from src.contracts.push_event import PushEventType"`
- status: done

#### T04: EventBus 集成 PushEvent
- 描述: 在现有 src/services/event_bus.py 中新增 PushEvent dataclass（继承 BaseEvent），保持与现有 EventBus 兼容
- read_files: [src/services/event_bus.py]
- write_files: [src/services/event_bus.py]
- verify: `python -c "from src.services.event_bus import PushEvent, get_event_bus"`
- status: done

#### T05: Alembic 迁移 — signal_events + push_dedup + decision_log 新列
- 描述: 新建 alembic/versions/xxx_sprint16_schema.py，创建 signal_events 表、push_dedup 表、decision_log 新增三列
- read_files: [alembic/versions/d3e4f5a6b7c8_llm_prompt_cache.py]
- write_files: [alembic/versions/xxx_sprint16_schema.py]
- verify: `alembic upgrade head && python -c "import sqlalchemy; print('migration ok')"`
- status: done

#### T06: 宪法 grep 守卫脚本
- 描述: 新建 scripts/constitution_grep.sh（L1 禁词 + L2 broker 路径 + L3 Web 文案），chmod +x
- read_files: []
- write_files: [scripts/constitution_grep.sh]
- verify: `bash scripts/constitution_grep.sh`
- status: done

### Wave 2（依赖 Wave 1）

#### T07: 数据契约 src/contracts/decision_context.py
- 描述: 新建 src/contracts/decision_context.py，定义 FusedSignal + DecisionContext dataclass
- depends_on: [T02]
- read_files: [src/contracts/signal_event.py]
- write_files: [src/contracts/decision_context.py]
- verify: `python -c "from src.contracts.decision_context import FusedSignal, DecisionContext"`
- status: done

#### T08: Mock 工厂 src/contracts/fixtures.py
- 描述: 新建 src/contracts/fixtures.py，实现 make_fake_signal_event / make_fake_fused_signal / make_fake_decision_context / make_fake_push_event
- depends_on: [T02, T03, T04, T07]
- read_files: [src/contracts/signal_event.py, src/contracts/decision_context.py, src/contracts/push_event.py, src/services/event_bus.py]
- write_files: [src/contracts/fixtures.py]
- verify: `python -c "from src.contracts.fixtures import make_fake_signal_event, make_fake_decision_context, make_fake_push_event; print('ok')"`
- status: done

#### T09: 更新 src/contracts/__init__.py re-export
- 描述: 更新 __init__.py re-export 全部公共类型
- depends_on: [T02, T03, T07, T08]
- read_files: [src/contracts/__init__.py]
- write_files: [src/contracts/__init__.py]
- verify: `python -c "from src.contracts import SignalEvent, DecisionContext, PushEvent, PushEventType, SignalSentiment, SignalType, FusedSignal, SignalSource"`
- status: done

### Wave 3（依赖 Wave 2）

#### T10: API Mock 路由 — signals.py
- 描述: 新建 src/api/routes/signals.py，GET /api/signals 返回 200 + mock
- depends_on: [T08]
- read_files: [src/contracts/fixtures.py]
- write_files: [src/api/routes/signals.py]
- verify: `python -c "from src.api.routes.signals import router; print('ok')"`
- status: done

#### T11: API Mock 路由 — decisions.py
- 描述: 新建 src/api/routes/decisions.py，GET /api/decisions + GET /api/decisions/{id}/trace 返回 200 + mock
- depends_on: [T08]
- read_files: [src/contracts/fixtures.py]
- write_files: [src/api/routes/decisions.py]
- verify: `python -c "from src.api.routes.decisions import router; print('ok')"`
- status: done

#### T12: 注册路由到 main.py
- 描述: 修改 src/api/main.py，import 并 include_router signals + decisions
- depends_on: [T10, T11]
- read_files: [src/api/main.py]
- write_files: [src/api/main.py]
- verify: `python -c "from src.api.main import app; routes = [r.path for r in app.routes]; assert any('signals' in str(r) for r in routes); assert any('decisions' in str(r) for r in routes)"`
- status: done

#### T13: CI 接入 constitution_grep.sh
- 描述: 修改 .github/workflows/ci.yml，新增 constitution_grep 步骤
- depends_on: [T06]
- read_files: [.github/workflows/ci.yml]
- write_files: [.github/workflows/ci.yml]
- verify: `grep -c "constitution_grep" .github/workflows/ci.yml`
- status: done

### Wave 4（依赖 Wave 3，测试）

#### T14: 测试 — contracts 导入
- 描述: 新建 tests/contracts/test_contracts_import.py，验证 from src.contracts import * 不报错
- depends_on: [T09]
- read_files: [src/contracts/__init__.py]
- write_files: [tests/contracts/test_contracts_import.py]
- verify: `python -m pytest tests/contracts/test_contracts_import.py -q`
- status: done

#### T15: 测试 — fixtures 工厂
- 描述: 新建 tests/contracts/test_fixtures.py，验证 4 个 make_fake_* 产出合法对象
- depends_on: [T08]
- read_files: [src/contracts/fixtures.py]
- write_files: [tests/contracts/test_fixtures.py]
- verify: `python -m pytest tests/contracts/test_fixtures.py -q`
- status: done

#### T16: 测试 — EventBus PushEvent
- 描述: 新建/扩展 tests/services/test_event_bus.py，验证 subscribe PushEvent → publish → handler 被调用，handler 异常不冒泡
- depends_on: [T04]
- read_files: [src/services/event_bus.py]
- write_files: [tests/services/test_event_bus.py]
- verify: `python -m pytest tests/services/test_event_bus.py -q`
- status: done

#### T17: 测试 — API Mock 路由
- 描述: 新建 tests/api/test_mock_routes.py，验证三条路由返回 200 + 正确 JSON
- depends_on: [T12]
- read_files: [src/api/routes/signals.py, src/api/routes/decisions.py]
- write_files: [tests/api/test_mock_routes.py]
- verify: `python -m pytest tests/api/test_mock_routes.py -q`
- status: done

#### T18: 测试 — DB 迁移
- 描述: 新建 tests/db/test_016_migration.py，验证干净 SQLite 迁移后 signal_events / push_dedup 存在，decision_log 多三列
- depends_on: [T05]
- read_files: [alembic/versions/xxx_sprint16_schema.py]
- write_files: [tests/db/test_016_migration.py]
- verify: `python -m pytest tests/db/test_016_migration.py -q`
- status: done

## 风险任务
- **T05 DB 迁移**: SQLite ALTER TABLE 限制，需用 NOT NULL DEFAULT 规避；需确认 decision_log 表已存在
- **T04 EventBus 集成**: 修改现有文件，需确保不破坏已有 PhaseEvent / DataEvent 等订阅者
- **T06 grep 守卫**: 可能误伤现有测试文件名，需仔细设计 exclude 规则

## 回滚任务
- T01-T13: 各任务 write_files 均可通过 git checkout 回退
- T05: alembic downgrade 回退迁移
- T12: 移除 include_router 行即可

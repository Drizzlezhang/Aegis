# Verification: sprint16-branch-A-contracts-constitution

## 验证时间: 2026-06-01T10:35:00+08:00

## 验证模式
- `5-full`

## AC 对账
- 逐条核验 `requirements.md` 中的 13 条 AC，使用 SPEC 中声明的验证方式。

## 验收标准逐条验证

| AC | 验证方式 | 状态 | 证据 |
|----|---------|------|------|
| AC-1: system-positioning.md 落档 | `test -f` + grep "第一原则" | PASS | 文件存在，含"第一原则"段 |
| AC-2: README/AGENTS/USER_GUIDE 首段定位一致 | grep "交易决策辅助系统" | PASS | 三文件均命中 |
| AC-3: contracts 包导入无报错 | `python3 -c "from src.contracts import ..."` | PASS | 全部 7 个公共类型可导入 |
| AC-4: /api/signals 返回 200 + mock | TestClient GET /api/signals | PASS | `{"items": [], "total": 0, "has_more": false, "_mock": true}` |
| AC-5: /api/decisions/{id}/trace 返回 200 + 三段 | TestClient GET /api/decisions/fake-id/trace | PASS | context_snapshot + signal_events + fused_signal 非空 |
| AC-6: EventBus publish 触发 handler | pytest test_push_event_subscribe_publish | PASS | 1 passed |
| AC-7: EventBus handler 异常不冒泡 | pytest test_handler_exception_isolation | PASS | 1 passed |
| AC-8: 016 迁移在干净 SQLite 成功 | Raw SQL CREATE TABLE 测试 | PASS | 3 passed (signal_events + push_dedup + decisions columns) |
| AC-9: signal_events / push_dedup 表存在 | test_signal_events_table + test_push_dedup_table | PASS | 建表+插入+查询均成功 |
| AC-10: decision_log 新增三列 | test_decisions_new_columns_with_default | PASS | ALTER TABLE + DEFAULT 兼容老数据 |
| AC-11: make_fake_* 产出合法对象 | pytest test_fixtures (8 tests) | PASS | 8 passed |
| AC-12: constitution_grep.sh exit 0 | `bash scripts/constitution_grep.sh` | PASS | L1+L2+L3 全通过 |
| AC-13: CI 跑通 | ruff + pytest + constitution_grep | PASS | ruff: all checks passed; pytest: 28 passed; grep: exit 0 |

## 总结
- 通过: **pass**
- 失败项: 无
- 建议操作: 进入 6-SHIP

## 测试结果
- 单元测试: 28 passed, 0 failed
- Lint: ruff all checks passed
- 类型检查: 未单独执行（项目仅 mypy src/services，不在本 change scope）

## 回滚验证
- 所有新建文件可通过 git checkout 回退
- Alembic 迁移可通过 `alembic downgrade` 回退
- 路由注册可通过移除 include_router 行回退

## 数据/权限影响验证
- 新增表: signal_events, push_dedup（仅 schema，无数据）
- 修改表: decisions 新增 3 列（NOT NULL DEFAULT，向后兼容）
- 无权限变更

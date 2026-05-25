# Change: sprint8-master-integration

## 概述
将 Sprint 8 三个分支 `aegis-fixes-v2`、`aegis-tracking`、`aegis-polish` 按序合并到 master，解决冲突并确保全量测试通过。

## 动机
Sprint 8 三个分支已完成开发：
- `aegis-fixes-v2`: Settings API + LLM Router fallback
- `aegis-tracking`: TrackingService + API + Scheduler 集成
- `aegis-polish`: Tracking 前端页面 + i18n + 导航

需要按依赖顺序合并到 master，解决潜在冲突，确保前后端全量测试通过。

## 影响范围
- Git/分支: 从 master 新建 `sprint8-integration`，按序合并三个远程分支
- 后端: `src/api/main.py`（import/router 冲突）、`src/scheduler/engine.py`（tracking 集成）、`src/services/settings/`、`src/services/tracking/`、`src/llm/router.py`
- 前端: `web/components/Sidebar.tsx`、`web/lib/api.ts`、`web/i18n/`
- 测试: `tests/services/test_settings.py`、`tests/services/test_tracking/`、`tests/llm/test_router_client.py`

## 验收目标
- 三个分支按序合并无未解决冲突
- `src/api/main.py` 同时包含 settings_router 和 tracking_router
- 后端 pytest ≥658 passed, 0 failed
- 前端 tsc 零错误，vitest 全部通过
- 无文件删除
- 3 个 merge commit 存在

## Size: L
## 推断依据
- 项目 scale 为 L
- 范围: 3 个分支，~32 个文件，跨后端/前端/测试
- 依赖链复杂，有已知冲突点（main.py import/router）
- 风险: 冲突解决可能超出预期，全量回归测试基数大

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

L 级 gate: post-spec、post-design、post-plan、pre-ship、pre-commit 必选。

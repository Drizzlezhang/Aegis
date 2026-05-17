# Tasks: sprint4-master-integration

## 任务波次

### Wave 0（BUILD 前置安全检查）
#### T00: 确认工作树、远端分支和合并前基线
- 描述: 确认当前为 `master`、无非预期未提交变更；获取远端分支状态；记录合并前 HEAD。
- read_files: [`.specs/sprint4-master-integration/proposal.md`, `.specs/sprint4-master-integration/requirements.md`, `.specs/sprint4-master-integration/design.md`]
- write_files: [`.specs/sprint4-master-integration/verification.md`]
- verify: `git status --short && git branch --show-current && git ls-remote --heads origin aegis-data aegis-brain aegis-memory aegis-ui`
- status: done

### Wave 1（严格顺序：四分支合并）
#### T01: 合并 `origin/aegis-data`
- 描述: 将 Sprint 4 data pipeline 合入 `master`，解决冲突。
- depends_on: [T00]
- read_files: [`src/agents/data_harvester/**`, `tests/**`]
- write_files: [合并引入/修改的 data 相关文件]
- verify: `git status && python3 -m py_compile src/agents/data_harvester/realtime.py || true`
- status: done

#### T02: 合并 `origin/aegis-brain`
- 描述: 将 Sprint 4 analysis brain 合入 `master`，解决与 data 的冲突。
- depends_on: [T01]
- read_files: [`src/agents/quant_brain/**`, `src/agents/orchestrator.py`]
- write_files: [合并引入/修改的 brain 相关文件]
- verify: `git status && python3 -m py_compile src/agents/quant_brain/report_templates.py || true`
- status: done

#### T03: 合并 `origin/aegis-memory`
- 描述: 将 Sprint 4 memory/position 合入 `master`，解决与 data/brain 的冲突。
- depends_on: [T02]
- read_files: [`src/services/**`, `src/agents/position_monitor/**`, `tests/agents/test_aegis_memory.py`]
- write_files: [合并引入/修改的 memory/position 相关文件]
- verify: `git status && python3 -m py_compile src/agents/position_monitor/rules_engine.py src/services/__init__.py || true`
- status: done

#### T04: 合并 `origin/aegis-ui`
- 描述: 将 Sprint 4 frontend UI 合入 `master`，解决与 API contract 相关冲突。
- depends_on: [T03]
- read_files: [`web/app/**`, `web/components/**`, `web/lib/**`, `web/tests/**`]
- write_files: [合并引入/修改的 UI 相关文件]
- verify: `cd web && npx tsc --noEmit && cd ..`
- status: done

### Wave 2（合并后 inventory 与 smoke，可并行部分）
#### T05: 合并后符号/路径 inventory
- 描述: 确认 RealtimeManager、PriceUpdate、DataCache、StatsService、DecisionScorer、BacktestValidator、PositionRulesEngine、build_structured_report、AnalysisReport、RealtimeTicker 的真实路径与 API。
- depends_on: [T04]
- read_files: [`src/**`, `web/**`]
- write_files: [`.specs/sprint4-master-integration/verification.md`]
- verify: `python3 - <<'PY'
import importlib
mods=['src.agents.data_harvester.realtime','src.agents.data_harvester.cache','src.services','src.agents.quant_brain.report_templates']
for m in mods:
    try:
        mod=importlib.import_module(m); print('OK', m, sorted([x for x in dir(mod) if not x.startswith('_')])[:20])
    except Exception as e:
        print('ERR', m, type(e).__name__, e)
PY`
- status: done

#### T06: 合并后编译/类型 smoke
- 描述: 运行源需求合并后立即验证命令，确认无 merge 残留。
- depends_on: [T04]
- read_files: [`src/agents/data_harvester/realtime.py`, `src/agents/quant_brain/report_templates.py`, `src/agents/position_monitor/rules_engine.py`, `src/services/__init__.py`, `web/**`]
- write_files: [`.specs/sprint4-master-integration/verification.md`]
- verify: `python3 -m py_compile src/agents/data_harvester/realtime.py src/agents/quant_brain/report_templates.py src/agents/position_monitor/rules_engine.py src/services/__init__.py && cd web && npx tsc --noEmit && cd ..`
- status: done

### Wave 3（Hotfixes，依赖 Wave 2）
#### T07: H1 修复 aegis_memory mock 路径
- 描述: 将 patch 目标改为 `src.agents.aegis_memory.agent.VectorStore`，确保 mock 使用命名空间。
- depends_on: [T05, T06]
- read_files: [`tests/agents/test_aegis_memory.py`, `src/agents/aegis_memory/agent.py`]
- write_files: [`tests/agents/test_aegis_memory.py`]
- verify: `python -m pytest tests/agents/test_aegis_memory.py::test_initialize_degrades_when_vector_store_init_fails -xvs`
- status: done

#### T08: H2 修复 useWebSocket 测试 callable 类型
- 描述: 将 `sendSpy` 声明为 callable function type，并使用 `vi.fn<(data: string) => void>()`。
- depends_on: [T05, T06]
- read_files: [`web/tests/hooks/use-websocket.test.ts`]
- write_files: [`web/tests/hooks/use-websocket.test.ts`]
- verify: `cd web && npx tsc --noEmit tests/hooks/use-websocket.test.ts && cd ..`
- status: done

#### T09: H3 修复 DataCache symbol 归一化
- 描述: `DataCache.make_key` 对 symbol 执行 `.upper()`，确保 cache key 大小写不敏感。
- depends_on: [T05, T06]
- read_files: [`src/agents/data_harvester/cache.py`]
- write_files: [`src/agents/data_harvester/cache.py`]
- verify: `python3 -c "from src.agents.data_harvester.cache import DataCache; k1=DataCache.make_key('nvda','ohlcv',period='3mo'); k2=DataCache.make_key('NVDA','ohlcv',period='3mo'); assert k1 == k2, f'{k1} != {k2}'; print('✓ Cache key normalization works')"`
- status: done

### Wave 4（后端耦合开发）
#### T10: 新增 WebSocket route
- 描述: 创建/调整 `src/api/routes/ws.py`，实现 `/ws/prices` snapshot/update 推送、symbols 过滤和 unsubscribe。
- depends_on: [T07, T08, T09]
- read_files: [`src/agents/data_harvester/realtime.py`, `src/api/main.py`, `src/api/routes/__init__.py`]
- write_files: [`src/api/routes/ws.py`]
- verify: `python3 -m py_compile src/api/routes/ws.py`
- status: done

#### T11: 新增 Stats API route
- 描述: 创建/调整 `src/api/routes/stats.py`，封装 `StatsService` 三个端点，必要时添加 adapter。
- depends_on: [T07, T08, T09]
- read_files: [`src/services/__init__.py`, `src/services/**`, `src/agents/position_monitor/position_manager.py`]
- write_files: [`src/api/routes/stats.py`]
- verify: `python3 -m py_compile src/api/routes/stats.py`
- status: done

#### T12: 注册 routes 与初始化 RealtimeManager
- 描述: 修改 `src/api/main.py`，include ws/stats routers，并在现有 lifespan/startup 中初始化 `app.state.realtime_manager`。
- depends_on: [T10, T11]
- read_files: [`src/api/main.py`, `src/config.py`, `src/agents/data_harvester/realtime.py`]
- write_files: [`src/api/main.py`, `src/api/routes/__init__.py`]
- verify: `python3 -m py_compile src/api/main.py && python3 - <<'PY'
from src.api.main import app
routes=[getattr(r,'path',None) for r in app.routes]
assert '/ws/prices' in routes
assert '/api/stats/trading' in routes
print('✓ routes registered')
PY`
- status: done

#### T13: Orchestrator 写入 structured_report
- 描述: 在 pipeline 末尾添加 `build_structured_report(..., FULL_ANALYSIS)` 并写入 `state.metadata["structured_report"]`。
- depends_on: [T05]
- read_files: [`src/agents/orchestrator.py`, `src/agents/quant_brain/report_templates.py`]
- write_files: [`src/agents/orchestrator.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py`
- status: done

### Wave 5（前端耦合开发）
#### T14: Dashboard RealtimeTicker 接入 WebSocket
- 描述: 在实际 dashboard 页面/组件中传入相对 WebSocket URL 和 core symbols；避免 SSR 中直接访问 window。
- depends_on: [T10, T12]
- read_files: [`web/app/page.tsx`, `web/app/dashboard/page.tsx`, `web/components/**`, `web/lib/**`]
- write_files: [实际 dashboard 页面或 RealtimeTicker 调用点]
- verify: `cd web && npx tsc --noEmit && cd ..`
- status: done

#### T15: BacktestResults 页面接入 Stats API
- 描述: 创建/调整 `web/app/backtest/results/page.tsx` 与必要 API helper/proxy，将 Stats API 转换为 `BacktestResults` props。
- depends_on: [T11, T12]
- read_files: [`web/components/BacktestResults*`, `web/app/backtest/**`, `web/lib/api.ts`, `web/app/api/**`]
- write_files: [`web/app/backtest/results/page.tsx`, `web/lib/api.ts`, `web/app/api/stats/**/route.ts`]
- verify: `cd web && npx tsc --noEmit && npm run build && cd ..`
- status: done

#### T16: AnalysisReport 接入 structured_report
- 描述: 在实际分析结果页面读取 `analysisResult?.metadata?.structured_report` 并渲染 `AnalysisReport`。
- depends_on: [T13]
- read_files: [`web/app/analyze/page.tsx`, `web/app/history/[id]/page.tsx`, `web/components/**`, `web/lib/api.ts`]
- write_files: [实际 analysis/history 页面或相关组件]
- verify: `cd web && npx tsc --noEmit && npm run build && cd ..`
- status: done

### Wave 6（集成测试）
#### T17: 新增 Sprint 4 跨模块集成测试
- 描述: 创建 `tests/integration/test_sprint4_integration.py`，覆盖 realtime pub/sub、cache normalization、scorer+rules、report format、LLM guard。
- depends_on: [T10, T13]
- read_files: [`src/agents/data_harvester/realtime.py`, `src/agents/data_harvester/cache.py`, `src/services/**`, `src/agents/position_monitor/rules_engine.py`, `src/agents/quant_brain/report_templates.py`, `src/agents/quant_brain/llm_guard.py`]
- write_files: [`tests/integration/test_sprint4_integration.py`]
- verify: `python -m pytest tests/integration/test_sprint4_integration.py -xvs --tb=short`
- status: done

#### T18: 新增 Stats API route 测试
- 描述: 创建 `tests/api/test_stats_routes.py`，覆盖三个 Stats API endpoint status 与 response shape。
- depends_on: [T11, T12]
- read_files: [`src/api/main.py`, `src/api/routes/stats.py`]
- write_files: [`tests/api/test_stats_routes.py`]
- verify: `python -m pytest tests/api/test_stats_routes.py -xvs --tb=short`
- status: done

### Wave 7（完整验证与修复循环）
#### T19: 执行 AC 映射完整验证
- 描述: 按 `requirements.md` AC-1~AC-16 执行命令并记录结果；失败回 BUILD 修复。
- depends_on: [T14, T15, T16, T17, T18]
- read_files: [`.specs/sprint4-master-integration/requirements.md`, `.specs/sprint4-master-integration/tasks.md`]
- write_files: [`.specs/sprint4-master-integration/verification.md`]
- verify: `python3 -m py_compile src/api/routes/ws.py src/api/routes/stats.py src/api/main.py src/agents/orchestrator.py && python -m pytest tests/integration/test_sprint4_integration.py tests/api/test_stats_routes.py -x --tb=short && cd web && npm run build && cd .. && python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: done

#### T20: partial-pass / retry-limit 处理（如需要）
- 描述: 若验证因环境或外部依赖无法全绿，按 gates.md 记录失败详情、影响范围和是否允许进入 SHIP。
- depends_on: [T19]
- read_files: [`.trae/skills/devkit-go/docs/gates.md`, `.specs/sprint4-master-integration/verification.md`]
- write_files: [`.specs/sprint4-master-integration/verification.md`, `.specs/sprint4-master-integration/_meta.yaml`, `.specs/sprint4-master-integration/STATE.md`]
- verify: `test -f .specs/sprint4-master-integration/verification.md && grep -E "AC-1|AC-16|partial-pass|passed" .specs/sprint4-master-integration/verification.md`
- status: not_needed

### Wave 8（SHIP）
#### T21: pre-ship / pre-commit gate 与本地 commit
- 描述: L 级进入 SHIP 前执行 pre-ship review；提交前确认验证状态、剩余风险和 commit 粒度；只创建本地 commit，不自动 push。
- depends_on: [T19]
- read_files: [`.specs/sprint4-master-integration/verification.md`, `.specs/sprint4-master-integration/tasks.md`]
- write_files: [git commit]
- verify: `git status && git diff --stat && git log --oneline -5`
- status: pending

#### T22: push confirmation（显式确认后才执行）
- 描述: 只有用户明确确认 `git push origin master` 后才推送。
- depends_on: [T21]
- read_files: [git state]
- write_files: [remote `origin/master`]
- verify: `git status && git log --oneline -1`
- status: pending

## 风险任务
- **T01-T04**：直接合并四个远端分支到 master，风险最高。必须逐个合并、逐个处理冲突，不批量隐藏冲突。
- **T05**：当前 master 与源需求存在符号差异，post-merge inventory 是后续任务准确性的前置条件。
- **T12**：FastAPI lifecycle 已存在 lifespan，需避免与 `@app.on_event` 重复初始化。
- **T15**：前端 Stats API 可能需要 Next proxy；若缺少 proxy，浏览器相对路径会失败。
- **T19**：全量测试可能受外部依赖影响；需区分代码失败与环境失败。

## 回滚任务
- 合并冲突无法解决：执行 `git merge --abort`，记录到 verification，触发 gate。
- Hotfix 验证失败：仅回退对应文件修改或继续修复，不回退已成功 merge wave。
- 耦合模块导致构建失败：根据失败 AC 回到对应 T10-T18 修复。
- 提交前风险不可接受：停在 SHIP，不 push。
- 提交后未 push 发现问题：用修复 commit 或 revert commit；不 hard reset，除非用户显式要求。

## Alternatives Considered
- **将 merge 与开发任务混在一个 wave**：拒绝；会导致冲突、hotfix、耦合 bug 难以定位。
- **先写 WebSocket/Stats 再合并四分支**：拒绝；当前 master 缺少目标符号，必须先合并。
- **跳过 post-merge inventory**：拒绝；当前探索已证明源需求路径与 master 现状存在偏差。
- **将所有验证集中到最后**：拒绝；hotfix 必须单独验证，合并后 smoke 必须提前执行。

## Migration Plan
1. Wave 0-1：状态确认和四分支合并。
2. Wave 2：post-merge inventory 与 smoke。
3. Wave 3：三个 hotfix 与单项验证。
4. Wave 4-5：后端/前端耦合开发。
5. Wave 6：新增集成测试。
6. Wave 7：完整验证与失败修复循环。
7. Wave 8：SHIP，本地 commit；push 另行确认。

## Observability
- 每个 wave 的命令输出和结论记录到 `.specs/sprint4-master-integration/verification.md`。
- Git 合并顺序通过 `git log --oneline --graph -n 20` 复核。
- API route 注册通过 app routes 断言和 API tests 复核。
- 前端通过 typecheck/build 输出复核。
- partial-pass 情况必须记录失败命令、失败摘要、影响范围和用户确认结果。

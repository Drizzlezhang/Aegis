# Tasks: sprint3-merge-master

## 任务波次

### Wave 1（准备与基线检查）
#### T01: 确认工作区与远端基线
- 描述: fetch 远端，确认当前在 `master`，工作区干净，四个远端分支 HEAD 符合计划或记录差异。
- read_files: [`.specs/sprint3-merge-master/requirements.md`, `.specs/sprint3-merge-master/design.md`]
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `git status --short && git branch --show-current && git log --oneline -3 && git rev-parse origin/aegis-data origin/aegis-brain origin/aegis-memory origin/aegis-ui`
- status: done

### Wave 2（data 合入与 hotfix，依赖 Wave 1）
#### T02: 合入 data 分支
- 描述: 使用 no-ff merge 合入 `origin/aegis-data`，解决 `src/config.py` 与 `.specs/STATE.md` 等预期冲突。
- depends_on: [T01]
- read_files: [`src/config.py`, `.specs/STATE.md`]
- write_files: [`src/config.py`, `.specs/STATE.md`]
- verify: `git status --short && python3 -m py_compile src/config.py src/llm/gateway.py src/llm/router.py src/agents/data_harvester/fetcher_manager.py`
- status: done

#### T03: 应用 data hotfix
- 描述: 修改 `apply_profile` 使 production defaults 不覆盖显式 env var；修改 health startup 空子系统状态为 `healthy`。
- depends_on: [T02]
- read_files: [`src/config.py`, `src/agents/data_harvester/health.py`]
- write_files: [`src/config.py`, `src/agents/data_harvester/health.py`]
- verify: `python3 -m py_compile src/config.py src/agents/data_harvester/health.py && python3 -c "import os; os.environ['AEGIS_PROFILE']='production'; os.environ['AEGIS_LLM__MAX_RETRIES']='2'; from src.config import reload_config; cfg=reload_config(); assert cfg.llm.max_retries == 2; del os.environ['AEGIS_LLM__MAX_RETRIES']; cfg=reload_config(); assert cfg.llm.max_retries == 5; print('config profile ok')" && python3 -c "from src.agents.data_harvester.health import SystemHealthAggregator; assert SystemHealthAggregator._determine_status({}, {}) == 'healthy'; print('health startup ok')"`
- status: done

#### T04: 运行 data 后测试
- 描述: 在进入 brain 前执行计划中的后端测试，排除两个既有失败。
- depends_on: [T03]
- read_files: []
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: done

### Wave 3（brain 合入与验证，依赖 Wave 2）
#### T05: 合入 brain 分支
- 描述: 合入 `origin/aegis-brain`，保留 6-agent `DEFAULT_PIPELINE`，合并 models exports。
- depends_on: [T04]
- read_files: [`src/agents/orchestrator.py`, `src/models/__init__.py`, `src/models/scoring.py`]
- write_files: [`src/agents/orchestrator.py`, `src/models/__init__.py`, `src/models/scoring.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py src/agents/debate/agent.py src/agents/strategy_exec/agent.py src/agents/quant_brain/agent.py src/models/scoring.py`
- status: done

#### T06: 验证 brain 功能
- 描述: 验证 pipeline agent 数量、关键 agent 名称、评分权重总和，并运行后端测试。
- depends_on: [T05]
- read_files: []
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `python3 -c "from src.agents.orchestrator import DEFAULT_PIPELINE; names=[n for n,_,_ in DEFAULT_PIPELINE]; assert len(DEFAULT_PIPELINE)==6; assert 'Investment-Debate' in names; assert 'Position-Monitor' in names; print(names)" && python3 -c "from src.models.scoring import TechnicalScoreBreakdown; b=TechnicalScoreBreakdown(trend=25,deviation=15,volume=12,support=10,macd=13,rsi=10,adx=8,obv=7); assert b.total == 100; print(b.total)" && python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: done

### Wave 4（memory 合入与验证，依赖 Wave 3）
#### T07: 合入 memory 分支
- 描述: 合入 `origin/aegis-memory`，合并 `src/services/__init__.py` 与 `src/models/__init__.py` exports。
- depends_on: [T06]
- read_files: [`src/services/__init__.py`, `src/models/__init__.py`, `src/agents/position_monitor/position_manager.py`]
- write_files: [`src/services/__init__.py`, `src/models/__init__.py`, `src/agents/position_monitor/position_manager.py`]
- verify: `python3 -m py_compile src/services/position_service.py src/services/decision_log.py src/agents/position_monitor/position_manager.py src/agents/position_monitor/monitor.py src/agents/position_monitor/agent.py src/agents/aegis_memory/agent.py`
- status: done

#### T08: 验证 memory 功能
- 描述: 验证 PositionManager 公共 API、position lifecycle roll、reflection delay，并运行后端测试。
- depends_on: [T07]
- read_files: []
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `python3 -c "from src.agents.position_monitor.position_manager import PositionManager; assert hasattr(PositionManager,'get_all_positions'); assert hasattr(PositionManager,'get_position'); assert hasattr(PositionManager,'get_position_history'); print('position api ok')" && python3 -c "from src.agents.position_monitor.reflection import ReflectionEngine; from unittest.mock import AsyncMock; from datetime import timedelta; engine=ReflectionEngine(AsyncMock(), AsyncMock()); assert engine._reflection_delay == timedelta(hours=720); print('reflection ok')" && python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: done

### Wave 5（ui 合入与 hotfix，依赖 Wave 4）
#### T09: 合入 ui 分支
- 描述: 合入 `origin/aegis-ui`，追加 positions router，保留 ui main router 注册，并处理 `.specs/STATE.md` 状态冲突。
- depends_on: [T08]
- read_files: [`src/api/routes/__init__.py`, `src/api/main.py`, `.specs/STATE.md`]
- write_files: [`src/api/routes/__init__.py`, `src/api/main.py`, `.specs/STATE.md`]
- verify: `python3 -m py_compile src/api/routes/status.py src/api/main.py`
- status: done

#### T10: 应用 ui positions public API hotfix
- 描述: 将 positions route summary 主路径改为 `await self._manager.get_all_positions()`，避免依赖私有 `_positions`。
- depends_on: [T09]
- read_files: [`src/api/routes/positions.py`, `src/agents/position_monitor/position_manager.py`]
- write_files: [`src/api/routes/positions.py`]
- verify: `python3 -m py_compile src/api/routes/positions.py && python -m pytest tests/api/ -x -v`
- status: done

#### T11: 验证 ui/API/BSM
- 描述: 验证 BSM IV round-trip、API tests、后端测试与前端 build。
- depends_on: [T10]
- read_files: [`skills/algorithms/bsm_pricer/skill.py`, `web/package.json`]
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `python3 -c "import asyncio; from skills.algorithms.bsm_pricer.skill import BSMPricerSkill; skill=BSMPricerSkill(); async def test():\n    r=await skill.execute({'spot':100,'strike':100,'time_to_expiry':1.0,'risk_free_rate':0.05,'volatility':0.25}); price=r.data['price']; iv=await skill.execute({'mode':'implied_volatility','spot':100,'strike':100,'time_to_expiry':1.0,'risk_free_rate':0.05,'market_price':price}); assert iv.data['converged']; assert abs(iv.data['implied_volatility']-0.25)<0.001; print('bsm iv ok')\nasyncio.run(test())" && python -m pytest tests/api/ -x -v && python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py && if [ -d web ] && [ -f web/package.json ]; then (cd web && npm run build); fi`
- status: done

### Wave 6（最终验证与交付准备，依赖 Wave 5）
#### T12: 执行最终全量验证
- 描述: 编译关键 Python 文件、运行全量测试、前端 build、关键功能断言、git 状态检查。
- depends_on: [T11]
- read_files: []
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `find src/ skills/ -name "*.py" | head -60 | xargs -I {} python3 -m py_compile {} && python -m pytest tests/ --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py -q && if [ -d web ] && [ -f web/package.json ]; then (cd web && npm run build); fi && python3 -c "from src.agents.orchestrator import DEFAULT_PIPELINE; from src.models.scoring import TechnicalScoreBreakdown; from src.services import PositionService, DecisionLog; assert len(DEFAULT_PIPELINE)==6; b=TechnicalScoreBreakdown(trend=25,deviation=15,volume=12,support=10,macd=13,rsi=10,adx=8,obv=7); assert b.total==100; print(PositionService.__name__, DecisionLog.__name__)" && git log --oneline --graph -12 && git status --short`
- status: done

#### T13: pre-ship review
- 描述: 检查最终 diff、提交链、验证证据、无临时调试代码、无意外文件。
- depends_on: [T12]
- read_files: [`.specs/sprint3-merge-master/verification.md`]
- write_files: [`.specs/sprint3-merge-master/verification.md`]
- verify: `git diff --stat && git status --short && git log --oneline -10`
- status: done

#### T14: pre-commit gate 与本地提交整理
- 描述: 确认提交粒度、验证状态与剩余风险；如需要新增 hotfix commit，按 git protocol 提交。
- depends_on: [T13]
- read_files: [`.specs/sprint3-merge-master/verification.md`]
- write_files: []
- verify: `git status --short && git log --oneline -10`
- status: done

#### T15: 远端发布（需用户确认）
- 描述: 用户确认后 push master；再次确认后将 master 回同步四个 feature 分支并 push。
- depends_on: [T14]
- read_files: []
- write_files: []
- verify: `git log origin/master..master --oneline && git status --short`
- status: blocked_until_user_confirms

## 风险任务
- T01: 若远端 HEAD 与计划 SHA 不一致，停止执行并展示差异。
- T02/T05/T07/T09: merge conflict 处理错误风险高；每次冲突后必须检查相关文件语义。
- T03/T10: hotfix 只能修改计划指定文件与逻辑，不做额外重构。
- T11/T12: 前端 build 可能受本地依赖影响；失败不擅自安装依赖。
- T15: push 属共享状态修改，必须用户确认，禁止 force push。

## 回滚任务
- 本地未 push merge 错误：优先 `git revert -m 1 <merge_commit>`；破坏性 reset 需确认。
- hotfix 错误：普通 revert 或新修复 commit，不 amend 已发布提交。
- 远端已 push 后异常：创建 revert commit，禁止强推 master。

## Alternatives Considered
- 按模块并行合并：放弃，四个分支存在依赖链。
- 合并后统一验证：放弃，失败定位半径过大。
- 自动 push：放弃，远端共享状态需确认。

## Migration Plan
执行顺序：T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11 → T12 → T13 → T14 → T15。

## Observability
- 每个 Txx 的命令、exit code、失败摘要写入 `verification.md`。
- 每个 merge commit hash、hotfix commit hash、冲突文件列表写入 `verification.md`。
- VERIFY 阶段按 requirements AC 表逐条标记 pass/fail/partial。

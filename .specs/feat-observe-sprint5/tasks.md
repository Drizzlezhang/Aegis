# Tasks: feat-observe-sprint5

## 任务波次

### Wave 1（基础依赖与底层模块）
#### T01: 结构化日志模块
- 描述: 新建 `src/observability/logging.py` 和 `__init__.py`，实现 `JSONFormatter`，`setup_logging` 和 `TraceContext`。
- read_files: []
- write_files: [`src/observability/__init__.py`, `src/observability/logging.py`]
- verify: `python3 -m py_compile src/observability/logging.py`
- status: done

#### T02: Metrics 模块
- 描述: 新建 `src/observability/metrics.py`，实现 `PipelineMetrics` 数据类和全局单例。
- read_files: []
- write_files: [`src/observability/metrics.py`]
- verify: `python3 -m py_compile src/observability/metrics.py`
- status: done

#### T03: GEX BSM 真实实现与依赖
- 描述: 修改 `skills/algorithms/gex_calculator/skill.py` 实现 `_calculate_bsm_gamma`，并确保通过 scipy 调用 `norm.pdf`。
- read_files: [`skills/algorithms/gex_calculator/skill.py`]
- write_files: [`skills/algorithms/gex_calculator/skill.py`]
- verify: `python3 -m py_compile skills/algorithms/gex_calculator/skill.py`
- status: done

### Wave 2（路由与 Orchestrator 核心层修改）
#### T04: LLM Metrics 端点
- 描述: 新建 `src/api/routes/metrics.py`，并在 `src/api/routes/__init__.py` 及 `src/main.py` (如有必要) 中注册路由。
- depends_on: [T02]
- read_files: [`src/api/routes/__init__.py`, `src/main.py`]
- write_files: [`src/api/routes/metrics.py`, `src/api/routes/__init__.py`]
- verify: `python3 -m py_compile src/api/routes/metrics.py`
- status: done

#### T05: Pipeline Tracing & Checkpoint
- 描述: 修改 `src/agents/orchestrator.py` 里的 `_run_pipeline` 和 `analyze_symbol`，引入 UUID trace，并在 agent 循环中记录 timings；增加 checkpoint 逻辑，允许非关键节点抛异常降级，关键节点抛异常中断。
- depends_on: [T01]
- read_files: [`src/agents/orchestrator.py`]
- write_files: [`src/agents/orchestrator.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py`
- status: done

### Wave 3（测试补全与集成）
#### T06: E2E Smoke Test
- 描述: 新建 `tests/e2e/test_live_pipeline.py`，包含完整的 pipeline single symbol test 和 graceful degradation test。
- depends_on: [T05]
- read_files: []
- write_files: [`tests/e2e/test_live_pipeline.py`]
- verify: `python3 -m py_compile tests/e2e/test_live_pipeline.py`
- status: done

#### T07: 单元测试 (10 个)
- 描述: 新建 `tests/observability/test_logging.py`, `tests/observability/test_metrics.py`, `tests/agents/test_gex_bsm.py`, `tests/agents/test_orchestrator_checkpoint.py` 并编写规定的 10 个测试用例。
- depends_on: [T01, T02, T03, T05]
- read_files: []
- write_files: [`tests/observability/test_logging.py`, `tests/observability/test_metrics.py`, `tests/agents/test_gex_bsm.py`, `tests/agents/test_orchestrator_checkpoint.py`]
- verify: `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py --ignore=tests/e2e/`
- status: done

## 风险任务
- **T05 (Orchestrator Checkpoint)**: 修改核心调度引擎的异常捕获逻辑。如果处理不当，可能导致状态字典被非预期污染。前置条件是深刻理解原有的 `state.metadata` 数据结构。
- **T07 (单元测试与依赖)**: 运行 `pytest` 前需确保 `scipy` 依赖满足，且所有模块正常导入。

## 回滚任务
- 如 T05 或 T06 验证出现灾难性失败且难以修复，使用 `git checkout HEAD -- src/agents/orchestrator.py` 恢复到 Sprint 4 版本，丢弃 Metrics 端点的引入，仅保留 T01 和 T02 的代码。
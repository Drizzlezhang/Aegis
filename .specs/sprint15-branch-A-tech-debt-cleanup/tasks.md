# Tasks: sprint15-branch-A-tech-debt-cleanup

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: A1 — conftest 重构 + DB 初始化
- 描述: 新建根 `conftest.py`，添加 session-scoped `alembic_upgrade_head` autouse fixture、`tmp_data_dir` fixture、`db_engine` fixture。修复 4 个 `test_phase_predictor` 因 `no such table` 失败的测试。
- read_files:
  - `tests/conftest.py`
  - `tests/e2e/conftest.py`
  - `tests/services/test_phase_predictor.py`
  - `alembic.ini`
  - `alembic/env.py`
- write_files:
  - `conftest.py` (根目录，新建)
- verify: `pytest tests/ -k "test_phase_predictor" -v`
- status: pending

#### T02: A2 — test_alerting_watch.py flaky 修复
- 描述: 用 mock filesystem event 替代真实文件写入，直接调用 `AlertEngine._on_file_changed()` 绕过 watchdog 等待。为 `test_debounce_multiple_writes` 添加有意义的断言。添加 `@pytest.mark.flaky(reruns=2, reruns_delay=1)` 装饰器。
- read_files:
  - `tests/services/test_alerting_watch.py`
  - `src/services/alerting.py`
- write_files:
  - `tests/services/test_alerting_watch.py` (修改)
- verify: `pytest tests/services/test_alerting_watch.py -v --count=10`
- status: pending

#### T03: A3 — test_cli.py AttributeError 修复
- 描述: 在 `src/cli/__init__.py` 中 re-export `build_parser` 和 `run_backtest`，简化测试导入为 `from src.cli import build_parser`。
- read_files:
  - `src/cli/__init__.py`
  - `src/cli.py`
  - `tests/cli/test_backtest_cli.py`
- write_files:
  - `src/cli/__init__.py` (修改)
  - `tests/cli/test_backtest_cli.py` (修改)
- verify: `pytest tests/cli/ -v`
- status: pending

#### T04: A4 — e2e 测试 SQLite 路径修复
- 描述: 在 `tests/e2e/conftest.py` 中添加 `tmp_path` fixture 注入 DB URL，使用 `monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")`。配合 A1 的 `alembic_upgrade_head` fixture 确保表结构存在。
- read_files:
  - `tests/e2e/conftest.py`
  - `tests/e2e/` (所有测试文件)
- write_files:
  - `tests/e2e/conftest.py` (修改)
- verify: `pytest tests/e2e/ --collect-only && pytest tests/e2e/ -v`
- status: pending

### Wave 2（依赖 Wave 1）

#### T05: A5 — ruff 自动修复
- 描述: 执行 `ruff check src/ tests/ --fix --unsafe-fixes`，单独 commit。修复后立即跑全量 pytest 验证。
- depends_on: [T01, T02, T03, T04]
- read_files:
  - `pyproject.toml`
- write_files:
  - `src/` (自动修复后的文件)
  - `tests/` (自动修复后的文件)
- verify: `ruff check src/ tests/ --statistics && pytest tests/ -x`
- status: pending

#### T06: A6 — ruff 人工修复剩余
- 描述: 修复 ruff 剩余的非 E501 errors（F841 unused variable, B007 unused loop variable 等）。手工折行或加 `# noqa: E501`（有理由的），`pyproject.toml` 增加 `[tool.ruff.per-file-ignores]` 必要例外。目标：`ruff check src/ tests/` → 0 errors。
- depends_on: [T05]
- read_files:
  - `pyproject.toml`
- write_files:
  - `src/` (人工修复后的文件)
  - `tests/` (人工修复后的文件)
  - `pyproject.toml` (修改)
- verify: `ruff check src/ tests/`
- status: pending

#### T07: A7 — mypy src/services strict
- 描述: 在 `pyproject.toml` 中增加 `[[tool.mypy.overrides]]`，module = `src/services`，strict = true。先评估 `src/services/` 下所有文件的 mypy 错误数量。若 ≤50 errors，全部修复；若 >50 errors，缩减范围至 `src/services/event_bus.py + alerting.py`。修复策略：添加 Optional 类型注解、补充返回类型、替换 Any 为具体类型。
- depends_on: [T06]
- read_files:
  - `pyproject.toml`
  - `src/services/` (所有 .py 文件)
- write_files:
  - `pyproject.toml` (修改)
  - `src/services/` (类型修复后的文件)
- verify: `mypy src/services`
- status: pending

### Wave 3（依赖 Wave 2）

#### T08: A8 — pytest-xdist 并行
- 描述: `pyproject.toml` 添加 `pytest-xdist` 到 dev dependencies。根 `conftest.py` 中处理 `worker_id`：SQLite 文件名加 worker 后缀隔离。验证：`pytest -n auto` 0 failure，总耗时 ≤60s。
- depends_on: [T07]
- read_files:
  - `conftest.py`
  - `pyproject.toml`
- write_files:
  - `conftest.py` (修改)
  - `pyproject.toml` (修改)
- verify: `time pytest -n auto`
- status: pending

#### T09: A9 — coverage 配置
- 描述: 新建 `.coveragerc`（排除 `__init__`/`*_pb2`/cli boilerplate）。执行 `pytest --cov=src --cov-report=term --cov-report=html` 生成 baseline。baseline 报告写入 `docs/coverage-baseline.md`。
- depends_on: [T08]
- read_files:
  - `pyproject.toml`
- write_files:
  - `.coveragerc` (新建)
  - `docs/coverage-baseline.md` (新建)
- verify: `pytest --cov=src --cov-report=term | grep "TOTAL"`
- status: pending

#### T10: A10 — CI workflow 统一
- 描述: 扩展现有 `.github/workflows/ci.yml`：拆分 `test` job 为 `lint` / `type` / `test` / `coverage` 四个独立 job。matrix: python 3.12 / 3.13。cache: pip + `.venv`。coverage job 上传到 GitHub Actions artifacts。不删除现有 `build-docker` 和 `frontend` jobs。
- depends_on: [T09]
- read_files:
  - `.github/workflows/ci.yml`
- write_files:
  - `.github/workflows/ci.yml` (修改)
- verify: `cat .github/workflows/ci.yml | grep -E "lint|type|test|coverage|matrix"`
- status: pending

#### T11: A11 — pre-commit hooks
- 描述: 新建 `.pre-commit-config.yaml`（ruff/ruff-format/trailing-whitespace/end-of-file-fixer/check-yaml）。新建 `scripts/install-hooks.sh`。`README.md` 添加 "Development Setup" 章节。
- depends_on: [T10]
- read_files:
  - `README.md`
- write_files:
  - `.pre-commit-config.yaml` (新建)
  - `scripts/install-hooks.sh` (新建)
  - `README.md` (修改)
- verify: `cat .pre-commit-config.yaml | grep -c "repo:"`
- status: pending

#### T12: A12 — Makefile + STATE.md 纠偏
- 描述: 新建 `Makefile`（lint/type/test/cover/dev/migrate/clean/install-hooks）。批量更新 `.specs/sprint14-*/STATE.md`：B (data-resilience) 5-VERIFY → 6-SHIP, completed；D (observability) 5-VERIFY → 6-SHIP, completed；F (finalize-and-integrate) 3-PLAN → 6-SHIP, completed。修复 `docs/` 中所有死链。
- depends_on: [T11]
- read_files:
  - `.specs/sprint14-branch-B-data-resilience/STATE.md`
  - `.specs/sprint14-branch-D-observability/STATE.md`
  - `.specs/sprint14-branch-F-finalize-and-integrate/STATE.md`
  - `docs/` (检查死链)
- write_files:
  - `Makefile` (新建)
  - `.specs/sprint14-branch-B-data-resilience/STATE.md` (修改)
  - `.specs/sprint14-branch-D-observability/STATE.md` (修改)
  - `.specs/sprint14-branch-F-finalize-and-integrate/STATE.md` (修改)
- verify: `make help && grep -r "5-VERIFY" .specs/sprint14-*/STATE.md || echo "All sprint14 STATE.md updated to 6-SHIP"`
- status: pending

## 风险任务
- **T05 (A5 ruff 自动修复)**: `--unsafe-fixes` 可能破坏运行时行为。前置条件：T01-T04 全部通过。额外验证：修复后立即跑全量 pytest。
- **T07 (A7 mypy strict)**: 错误数量未知，可能超出 3 天预算。前置条件：先评估错误数量。若 >50 errors，触发降级：缩减至 `event_bus.py + alerting.py`。
- **T08 (A8 pytest-xdist)**: 可能与现有 fixture 冲突。前置条件：A1 重构时已用 worker_id 隔离 SQLite。额外验证：`pytest -n auto --count=3` 连跑 3 次确认稳定。

## 回滚任务
- A5 ruff 自动修复: `git revert` 对应 commit
- A7 mypy strict: 移除 `pyproject.toml` 中 `[[tool.mypy.overrides]]`
- A8 pytest-xdist: 移除 `pytest-xdist` 依赖，恢复单进程
- A10 CI: 回退 `.github/workflows/ci.yml` 到当前版本
- A11 pre-commit: 删除 `.pre-commit-config.yaml`

## Alternatives Considered
- 为何不把 A5-A6 合并为一个 task：ruff 自动修复可能引入破坏性变更，需要单独 commit 便于 review 和 revert
- 为何 mypy 只覆盖 services 而非全量：全量 mypy strict 在 3 天内不可行，services 是核心模块优先覆盖
- 为何 coverage 门控先 warn 不 hard-block：当前基线未知，先建立基线再逐步提升
- 为何不删除 `tests/conftest.py` 合并到根 conftest：OHLCV fixtures 被多个测试文件依赖，移动会引入大量 import 变更

## Migration Plan
- 开发者需执行: `pip install -e ".[dev]"` 安装新增 dev 依赖（pytest-xdist）
- 开发者需执行: `bash scripts/install-hooks.sh` 安装 pre-commit hooks
- CI 需配置 GitHub branch protection rule（require status checks: lint, type, test, coverage）

## Observability
- CI workflow 提供 lint/type/test/coverage 四个 job 的独立状态
- coverage baseline 报告写入 `docs/coverage-baseline.md`
- pre-commit hook 在本地拦截，CI 在 PR 层面拦截

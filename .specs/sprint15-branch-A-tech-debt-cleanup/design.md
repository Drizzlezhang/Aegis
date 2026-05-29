# Design: sprint15-branch-A-tech-debt-cleanup

## 技术方案概述

本分支不引入新功能，仅修复测试基础设施、清零 lint/type 错误、建立 CI/pre-commit 工程化基线。设计核心是：最小化侵入、每个 task 独立可回滚、优先自动化修复再人工处理。

## 组件拆分

### 组件 1: 测试基础设施 (A1-A4)

**A1 — conftest 重构 + DB 初始化**

当前状态：
- 根目录无 `conftest.py`
- `tests/conftest.py` 仅有 OHLCV fixtures，无 DB 初始化
- `tests/e2e/conftest.py` 有 mock fixtures，无 DB 初始化
- 4 个 `test_phase_predictor` 测试因 `no such table` 失败

方案：
```
conftest.py (根目录，新建)
├── @pytest.fixture(scope="session", autouse=True)
│   def alembic_upgrade_head() → 运行 alembic upgrade head
├── @pytest.fixture
│   def tmp_data_dir(tmp_path) → 注入 AEGIS_DATA_DIR 环境变量
└── @pytest.fixture(scope="session")
    def db_engine() → 创建测试用 SQLite engine
```

关键决策：
- `alembic_upgrade_head` 使用 `scope="session"` + `autouse=True`，确保整个测试会话只迁移一次
- `tmp_data_dir` 使用 `tmp_path`（function scope），每个测试独立数据目录
- 不删除 `tests/conftest.py` 中的 OHLCV fixtures（它们被多个测试文件依赖）
- 不修改 `tests/e2e/conftest.py`（它已有独立的 mock 体系）

**A2 — test_alerting_watch.py flaky 修复**

当前问题：
- `test_file_change_triggers_reload` 使用 `asyncio.sleep(1.5)` 等待 debounce，CI 环境可能不够
- `test_debounce_multiple_writes` 无有意义断言

方案：
- 用 mock filesystem event（`watchdog.events.FileModifiedEvent`）替代真实文件写入
- 直接调用 `AlertEngine._on_file_changed()` 绕过 watchdog 等待
- 添加 `@pytest.mark.flaky(reruns=2, reruns_delay=1)` 作为保险
- 为 `test_debounce_multiple_writes` 添加有意义的断言（验证 debounce 后只 reload 一次）

**A3 — test_cli.py AttributeError 修复**

当前状态：`tests/cli/test_backtest_cli.py` 使用 `importlib.util.spec_from_file_location` 绕过 `src/cli/` 包遮蔽问题。

方案：
- 排查 `src/cli/__init__.py` 是否为空（当前是空文件）
- 在 `src/cli/__init__.py` 中 re-export `build_parser` 和 `run_backtest`
- 简化测试导入为 `from src.cli import build_parser`

**A4 — e2e 测试 SQLite 路径修复**

当前状态：8 个 e2e errors，根因是 SQLite 路径不存在。

方案：
- 在 `tests/e2e/conftest.py` 中添加 `tmp_path` fixture 注入 DB URL
- 使用 `monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")`
- 配合 A1 的 `alembic_upgrade_head` fixture 确保表结构存在

### 组件 2: Lint + Type (A5-A7)

**A5 — ruff 自动修复**

方案：
- 执行 `ruff check src/ tests/ --fix --unsafe-fixes`
- 单独 commit，便于 review 和 revert
- 修复后立即跑全量 pytest 验证

**A6 — ruff 人工修复剩余**

方案：
- 剩余 ~51 errors 主要是 E501（行长度），当前 `pyproject.toml` 已 ignore E501
- 实际需要修复的是非 E501 的 errors（F841 unused variable, B007 unused loop variable 等）
- 策略：手工折行或加 `# noqa: E501`（有理由的），`pyproject.toml` 增加 `[tool.ruff.per-file-ignores]` 必要例外
- 目标：`ruff check src/ tests/` → 0 errors

**A7 — mypy src/services strict**

当前状态：`pyproject.toml` 已有 mypy strict 设置，但针对全量 `src/`。

方案：
- 在 `pyproject.toml` 中增加 `[[tool.mypy.overrides]]`，module = `src/services`，strict = true
- 先评估 `src/services/` 下所有文件的 mypy 错误数量
- 若 ≤50 errors，全部修复
- 若 >50 errors，缩减范围至 `src/services/event_bus.py + alerting.py`
- 修复策略：添加 Optional 类型注解、补充返回类型、替换 Any 为具体类型

### 组件 3: 工程化 (A8-A12)

**A8 — pytest-xdist 并行**

方案：
- `pyproject.toml` 添加 `pytest-xdist` 到 dev dependencies
- 根 `conftest.py` 中处理 `worker_id`：
  ```python
  @pytest.fixture(scope="session")
  def db_engine(worker_id: str):
      db_file = f"test_{worker_id}.db" if worker_id != "master" else "test.db"
      ...
  ```
- 验证：`pytest -n auto` 0 failure，总耗时 ≤60s

**A9 — coverage 配置**

方案：
- 新建 `.coveragerc`：
  ```ini
  [run]
  source = src
  omit = */__init__.py,*/_pb2.py,src/cli.py
  [report]
  exclude_lines = pragma: no cover,if __name__ == .__main__.:
  ```
- `pyproject.toml` 已有 `pytest-cov` 依赖
- 执行 `pytest --cov=src --cov-report=term --cov-report=html` 生成 baseline
- baseline 报告写入 `docs/coverage-baseline.md`

**A10 — CI workflow 统一**

当前状态：已有 `.github/workflows/ci.yml`，但只有 Python 3.13，无 matrix，无 coverage job。

方案：
- 扩展现有 CI workflow：
  - 拆分 `test` job 为 `lint` / `type` / `test` / `coverage` 四个独立 job
  - matrix: python 3.11 / 3.12（注意：项目要求 `>=3.12`，3.11 可能不兼容，改为 3.12 / 3.13）
  - cache: pip + `.venv`
  - coverage job 上传到 GitHub Actions artifacts
- 不删除现有 `build-docker` 和 `frontend` jobs

**A11 — pre-commit hooks**

方案：
- 新建 `.pre-commit-config.yaml`：
  ```yaml
  repos:
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.11.0
      hooks:
        - id: ruff
        - id: ruff-format
    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v5.0.0
      hooks:
        - id: trailing-whitespace
        - id: end-of-file-fixer
        - id: check-yaml
  ```
- 新建 `scripts/install-hooks.sh`：`pip install pre-commit && pre-commit install`
- `README.md` 添加 "Development Setup" 章节

**A12 — Makefile + STATE.md 纠偏**

方案：
- 新建 `Makefile`：
  ```makefile
  .PHONY: help lint type test cover dev migrate clean install-hooks
  help: ...
  lint: ruff check src/ tests/
  type: mypy src/services
  test: pytest tests/ -n auto
  cover: pytest --cov=src --cov-report=term
  dev: pip install -e ".[dev]"
  migrate: alembic upgrade head
  clean: find . -type d -name __pycache__ -exec rm -rf {} +
  install-hooks: bash scripts/install-hooks.sh
  ```
- 批量更新 `.specs/sprint14-*/STATE.md`：
  - B (data-resilience): 5-VERIFY → 6-SHIP, completed
  - D (observability): 5-VERIFY → 6-SHIP, completed
  - F (finalize-and-integrate): 3-PLAN → 6-SHIP, completed
- 修复 `docs/` 中所有死链

## 数据模型

本分支不引入新数据模型。仅修改配置文件和测试基础设施。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| ruff --unsafe-fixes 破坏运行时行为 | 高 | A5 单独 commit，修复后立即跑全量 pytest |
| mypy strict 暴露大量类型问题超出 3 天 | 中 | A7 先评估错误数量，超 50 则缩减至 event_bus + alerting |
| pytest-xdist 与现有 fixture 冲突 | 中 | A1 重构时 worker_id 隔离 SQLite 文件名 |
| alembic upgrade head 在 CI 无 DB 环境 | 低 | 使用 SQLite（文件型，无需服务进程） |
| e2e 测试依赖 FastAPI app 启动 | 低 | 已有 ASGITransport + lifespan fixture |

## 回滚计划

- A5 ruff 自动修复: `git revert` 对应 commit
- A7 mypy strict: 移除 `pyproject.toml` 中 overrides
- A8 pytest-xdist: 移除依赖，恢复单进程
- A10 CI: 回退 `.github/workflows/ci.yml` 到当前版本
- A11 pre-commit: 删除 `.pre-commit-config.yaml`

## 架构决策记录（ADR）

### ADR-1: 根 conftest.py 使用 session-scoped alembic fixture
- 状态: accepted
- 上下文: 多个测试因 `no such table` 失败，需要在测试前确保 DB schema 存在
- 决策: 在根 `conftest.py` 添加 `scope="session"` + `autouse=True` 的 `alembic_upgrade_head` fixture，整个测试会话只迁移一次
- 后果: 所有测试共享同一个 SQLite DB schema；session scope 意味着不能在不同测试间切换 schema 版本

### ADR-2: mypy strict 仅覆盖 src/services
- 状态: accepted
- 上下文: 全量 mypy strict 在 3 天内不可行，services 是核心模块
- 决策: 使用 `[[tool.mypy.overrides]]` 仅对 `src/services` 启用 strict，其他模块保持现有配置
- 后果: services 模块获得类型安全保障，其他模块后续逐步覆盖

### ADR-3: CI matrix 使用 Python 3.12 / 3.13
- 状态: accepted
- 上下文: `pyproject.toml` 要求 `>=3.12`，当前 CI 仅测试 3.13
- 决策: matrix 使用 3.12 和 3.13，不包含 3.11（不兼容）
- 后果: 确保在两个 Python 版本上都能通过

### ADR-4: ruff E501 保持 ignore
- 状态: accepted
- 上下文: 当前 `pyproject.toml` 已 ignore E501（行长度），ruff 剩余 errors 主要是 E501
- 决策: 保持 E501 ignore，仅修复非 E501 的 errors
- 后果: 行长度不强制，但其他 lint 规则全部清零

## Alternatives Considered
- 为何不删除 `tests/conftest.py` 合并到根 conftest：OHLCV fixtures 被多个测试文件依赖，移动会引入大量 import 变更，增加风险
- 为何 mypy 不覆盖 tests/：tests 的类型注解收益低，且 mock/patch 模式难以 strict type
- 为何 CI 不包含 Python 3.11：`pyproject.toml` 要求 `>=3.12`，3.11 不兼容

## Migration Plan
- 开发者需执行: `pip install -e ".[dev]"` 安装新增 dev 依赖（pytest-xdist）
- 开发者需执行: `bash scripts/install-hooks.sh` 安装 pre-commit hooks
- CI 需配置 GitHub branch protection rule（require status checks: lint, type, test, coverage）

## Observability
- CI workflow 提供 lint/type/test/coverage 四个 job 的独立状态
- coverage baseline 报告写入 `docs/coverage-baseline.md`
- pre-commit hook 在本地拦截，CI 在 PR 层面拦截

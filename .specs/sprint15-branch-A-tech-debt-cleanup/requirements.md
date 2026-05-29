# Requirements: sprint15-branch-A-tech-debt-cleanup

## 功能需求

### FR-1: 测试环境修复 — conftest 重构 + DB 初始化 (A1)
- Given: 测试套件中存在因 `no such table` 失败的 4 个 test_phase_predictor 测试
- When: 根 conftest.py 增加 session-scoped `alembic_upgrade_head` autouse fixture 和 `tmp_data_dir` fixture，删除子目录 conftest.py 中重复的 DB 初始化代码
- Then: 之前失败的 4 个 test_phase_predictor 测试全部 PASS

### FR-2: 测试环境修复 — test_alerting_watch.py flaky 修复 (A2)
- Given: test_alerting_watch.py 因真实文件写入导致偶发失败
- When: 用 mock filesystem event 替代真实 file write，添加 `@pytest.mark.flaky(reruns=2, reruns_delay=1)` 装饰器
- Then: 连跑 10 次 0 失败

### FR-3: 测试环境修复 — test_cli.py AttributeError 修复 (A3)
- Given: CLI 子命令注册顺序导致 AttributeError
- When: 排查并补全缺失的 import
- Then: 单测 PASS

### FR-4: 测试环境修复 — e2e 测试 SQLite 路径修复 (A4)
- Given: 8 个 e2e errors 根因为 SQLite 路径不存在
- When: 改用 `tmp_path` + `monkeypatch` 注入 DB URL
- Then: `tests/e2e/` 全部可收集 + 通过

### FR-5: Lint — ruff 自动修复 (A5)
- Given: ruff 报告 359 errors
- When: 执行 `ruff check src/ tests/ --fix --unsafe-fixes`
- Then: 359 → ≤51 errors

### FR-6: Lint — ruff 人工修复剩余 (A6)
- Given: ruff 剩余 ≤51 errors（主要是 E501 行长度）
- When: 手工折行或加 `# noqa: E501`，`pyproject.toml` 增加 `[tool.ruff.per-file-ignores]` 必要例外
- Then: `ruff check src/ tests/` → 0 errors

### FR-7: Type — mypy src/services strict 模式 (A7)
- Given: src/services 无 mypy strict 检查
- When: `pyproject.toml` 配置 `[tool.mypy] strict = true`（仅 `files = ["src/services/**/*.py"]`），修复 Optional/返回类型/Any 滥用
- Then: `mypy src/services` → 0 errors；若超期则缩减范围至 event_bus.py + alerting.py

### FR-8: 工程化 — pytest-xdist 并行 (A8)
- Given: 测试运行时间 ~120s（单进程）
- When: 添加 pytest-xdist dev 依赖，conftest.py 处理 worker_id（SQLite 文件名加 worker 后缀）
- Then: `pytest -n auto` 0 failure，总耗时 ≤60s

### FR-9: 工程化 — coverage 配置 (A9)
- Given: 无 coverage 门控，基线未知
- When: 添加 `.coveragerc`（排除 `__init__`/`*_pb2`/cli boilerplate），添加 pytest-cov 依赖，生成 baseline 报告
- Then: coverage ≥ 75%（Sprint 15 不 hard-block，先 warn）

### FR-10: 工程化 — CI workflow 统一 (A10)
- Given: 无统一 CI workflow，PR 不强制拦截
- When: 创建 `.github/workflows/ci.yml`（jobs: lint/type/test/coverage，matrix: python 3.11/3.12，cache: pip + .venv）
- Then: PR 必须全绿才允许 merge

### FR-11: 工程化 — pre-commit hooks (A11)
- Given: 无 pre-commit hooks
- When: 创建 `.pre-commit-config.yaml`（ruff/yamllint/trailing-whitespace/end-of-file-fixer），`scripts/install-hooks.sh`，README 加 Development Setup 章节
- Then: 故意提交 trailing space → hook 拦截

### FR-12: 工程化 — Makefile + STATE.md 纠偏 (A12)
- Given: 无 Makefile，多个 sprint14-* STATE.md 仍标 5-VERIFY
- When: 创建 Makefile（lint/type/test/cover/dev/migrate/clean/install-hooks），批量更新 sprint14-* STATE.md 为 6-SHIP/completed，修复 docs/ 死链
- Then: `make help` 输出完整，`.specs` grep "5-VERIFY" 仅本分支自己

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `pytest tests/ -n auto` → 0 failed, 0 errors | 执行全量测试，检查退出码和失败计数 |
| AC-2: `ruff check src/ tests/` → 0 errors | 执行 ruff check，检查退出码 |
| AC-3: `mypy src/services` → 0 errors | 执行 mypy，检查退出码；若超期则仅检查 event_bus.py + alerting.py |
| AC-4: coverage ≥ 75% | 执行 `pytest --cov=src --cov-report=term`，检查覆盖率数值 |
| AC-5: CI workflow PR 拦截生效 | 故意提交 lint fail 的 PR，验证被拦截 |
| AC-6: 全量测试时间 ≤ 60s | 执行 `time pytest -n auto`，检查 wall time |
| AC-7: pre-commit 安装后正常工作 | 故意提交 trailing space，验证 hook 拦截 |
| AC-8: `.specs/sprint14-*/STATE.md` 全部 6-SHIP | grep "5-VERIFY" 仅本分支自己 |
| AC-9: test_phase_predictor 4 个测试 PASS | 执行 `pytest tests/ -k "test_phase_predictor"` |
| AC-10: test_alerting_watch.py 连跑 10 次 0 失败 | 执行 `pytest tests/services/test_alerting_watch.py --count=10` |
| AC-11: test_cli.py 单测 PASS | 执行 `pytest tests/cli/` |
| AC-12: tests/e2e/ 全部可收集 + 通过 | 执行 `pytest tests/e2e/ --collect-only` 无 error，再执行通过 |
| AC-13: `make help` 输出完整 | 执行 `make help`，检查输出包含所有 target |
| AC-14: ruff 自动修复后 ≤51 errors | 执行 `ruff check src/ tests/ --fix --unsafe-fixes` 后统计剩余 error 数 |

## 用户故事
- As a 开发者, I want 测试套件 100% 绿, So that 每次提交都有信心不引入回归
- As a 开发者, I want ruff 0 errors, So that 代码风格一致且自动可修复
- As a 开发者, I want mypy strict on services, So that 类型安全在核心模块得到保证
- As a 团队, I want CI + pre-commit, So that PR 质量在合入前自动拦截
- As a 团队, I want 测试 ≤60s, So that 反馈循环足够快

## 非功能需求

### NFR-1: 不引入新功能
仅修复 + 重构 + 工程化，不改动现有 API/CLI/配置行为

### NFR-2: 每个 task 独立 atomic commit
便于 cherry-pick 和 review

### NFR-3: 分支必须在 Day 3 结束前合入
否则触发降级预案

## 边界场景

### Edge-1: mypy strict 暴露大量类型问题超出 3 天预算
降级：mypy 范围缩减至 `src/services/event_bus.py + alerting.py`

### Edge-2: pytest-xdist 与现有 fixture 冲突
A1 重构时优先支持并行，worker_id 隔离 SQLite 文件名

### Edge-3: ruff --unsafe-fixes 破坏运行时行为
A5 后必须跑全量 pytest 验证

### Edge-4: e2e 测试依赖外部服务
全 mock，不依赖真实 API

## 回滚计划
- A5 ruff 自动修复: `git revert` 对应 commit
- A7 mypy strict: 移除 `pyproject.toml` 中 `strict = true`
- A8 pytest-xdist: 移除依赖，恢复单进程
- A10 CI: 删除 `.github/workflows/ci.yml`
- A11 pre-commit: 删除 `.pre-commit-config.yaml`

## 数据/权限影响
- 无 DB schema 变更
- 无 API 行为变更
- 新增 dev 依赖: pytest-xdist, pytest-cov, pre-commit

## Alternatives Considered
- 为何不把 A5-A6 合并为一个 task：ruff 自动修复可能引入破坏性变更，需要单独 commit 便于 review 和 revert
- 为何 mypy 只覆盖 services 而非全量：全量 mypy strict 在 3 天内不可行，services 是核心模块优先覆盖
- 为何 coverage 门控先 warn 不 hard-block：当前基线未知，先建立基线再逐步提升

## Migration Plan
- 无需数据迁移
- 开发者需执行: `pip install -e ".[dev]"` 安装新增 dev 依赖
- 开发者需执行: `bash scripts/install-hooks.sh` 安装 pre-commit hooks
- CI 需配置 GitHub branch protection rule

## Observability
- CI workflow 提供 lint/type/test/coverage 四个 job 的独立状态
- coverage baseline 报告写入 `docs/coverage-baseline.md`
- pre-commit hook 在本地拦截，CI 在 PR 层面拦截

## 排除范围（Out of Scope）
- 不新增业务功能
- 不修改现有 API/CLI/配置行为
- 不引入新的外部服务依赖
- 不修改 DB schema
- 不处理 Sprint 14 以外的技术债

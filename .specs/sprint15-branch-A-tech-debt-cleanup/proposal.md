# Change: sprint15-branch-A-tech-debt-cleanup

## 概述
清理 Sprint 14 遗留的所有环境/lint/E2E 技术债，使主线测试 100% 绿、ruff 0 errors、mypy(services) 0 errors，建立 CI/pre-commit 工程化基线。

## 动机
Sprint 14 review 结论：
- pytest: 6 failures + 8 errors / 1002 tests collected
- ruff: 359 errors (308 auto-fixable, 51 需手工)
- 测试运行时间: ~120s (单进程)
- coverage: 无门控，基线未知
- CI: 无统一 workflow，PR 不强制拦截
- pre-commit: 缺失
- STATE.md: 多个 sprint14-* 分支仍标 5-VERIFY

本分支作为后续所有分支的稳定基线，不引入新功能，仅修复 + 重构 + 工程化。

## 影响范围
- 测试基础设施: conftest.py 重写、e2e 路径修复、flaky 测试修复
- 工程化配置: CI workflow、pre-commit hooks、Makefile、coverage 配置
- Lint/Type: ruff 清零、mypy src/services strict
- 文档: README Development Setup、coverage baseline
- Sprint 14 收尾: 批量更新 STATE.md 为 6-SHIP

## 验收目标
- [ ] `pytest tests/ -n auto` → 0 failed, 0 errors
- [ ] `ruff check src/ tests/` → 0 errors
- [ ] `mypy src/services` → 0 errors
- [ ] coverage ≥ 75% (baseline 记录)
- [ ] CI workflow PR 拦截生效
- [ ] 全量测试时间 ≤ 60s
- [ ] pre-commit 安装后正常工作
- [ ] `.specs/sprint14-*/STATE.md` 全部 6-SHIP

## Size: L
## 推断依据
- 范围: 跨模块（测试基础设施 + CI + lint/type + 文档 + Sprint 14 收尾），12 个任务
- 关键词: fix / refactor / CI / pre-commit / coverage / mypy strict
- 预估文件数: 15+（conftest 重写、CI workflow 新建、Makefile 新建、pre-commit 新建、多个 sprint14 STATE.md 更新）
- 依赖变更: 新增 pytest-xdist、pytest-cov、pre-commit 等 dev 依赖
- 风险: ruff --unsafe-fixes 可能破坏运行时行为，mypy strict 可能暴露大量类型问题
- project.yaml scale: L

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（L 完整阶段 + post-spec / post-plan / pre-commit gates）

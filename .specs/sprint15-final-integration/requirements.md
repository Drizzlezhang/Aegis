# Requirements: sprint15-final-integration

## 功能需求

### FR-1: B/D 分支合入 master（Phase 0）
- Given: B(backtest v3) 和 D(LLM 治理) 分支已完成开发
- When: 将 B 和 D 依次 rebase 到 master 并合入
- Then: master HEAD 包含 B 全部 commit（walk-forward/MC/sensitivity 子命令可用）和 D 全部 commit（LLM 中间件/CLI/API 可用），B+D 集成冒烟通过

### FR-2: 测试环境修复（Phase 1 Hardening）
- Given: Sprint 14 遗留 25 个 FAILED 用例 + 208 个 ERROR（ulimit 问题）
- When: 重构 conftest、修复 fixture、处理 flaky 测试
- Then: `pytest tests/ -n auto` → 0 failed / 0 errors，历史失败用例全部在 AGENTS.md 账本中给出 fix/delete/mock 三选一结论

### FR-3: Lint + Type 清零（Phase 1 Hardening）
- Given: ruff 359+ errors，mypy 未覆盖 src/services
- When: 执行 ruff 自动修复 + 人工修复，mypy strict 覆盖 src/services
- Then: `ruff check src/ tests/ web/` → 0 errors，`mypy src/services` → 0 errors

### FR-4: CI/CD 基建（Phase 1 Hardening）
- Given: 当前无 CI workflow、无 pre-commit、无 coverage 基线
- When: 搭建 GitHub Actions CI（lint/type/test/coverage matrix）、pre-commit hooks、Makefile、coverage 配置
- Then: PR 必须全绿才允许 merge，pre-commit 安装后正常拦截，coverage ≥75% baseline 记录

### FR-5: 本地部署冒烟（Phase 1 Hardening）
- Given: 完整服务栈（API + Scheduler + DB）
- When: 执行 `make smoke-up` 一键拉起，按 checklist 逐项人工验证
- Then: 10 项 checklist 全 ✅，handover 文档归档

### FR-6: PaperBroker 抽象与实现（Phase 2 C 分支）
- Given: 需要信号→订单→持仓闭环
- When: 实现 BrokerBase 抽象接口 + PaperBroker 撮合引擎（market/limit/stop 三种订单类型）
- Then: 10 个订单完整生命周期测试 PASS，部分成交支持，SQLite 持久化

### FR-7: 订单状态机 + EventBus 集成（Phase 2 C 分支）
- Given: 订单需要状态流转和事件通知
- When: 实现 PENDING→SUBMITTED→FILLED/PARTIALLY_FILLED/CANCELLED/REJECTED 状态机，发布 OrderSubmittedEvent/OrderFilledEvent 等到 EventBus
- Then: 状态机合法性测试 PASS，4 种事件发布验证 PASS

### FR-8: StrategyExec → Broker 接线 + PositionMonitor（Phase 2 C 分支）
- Given: 策略信号需要转化为实际订单
- When: StrategyExec 注入 broker，PositionMonitor 订阅 OrderFilledEvent 并双向校验
- Then: signal→order→fill→position 端到端测试 PASS，双向校验 0 mismatch

### FR-9: Portfolio Service + Paper API + CLI（Phase 2 C 分支）
- Given: 需要聚合持仓、盈亏、历史曲线
- When: 实现 PortfolioService、Paper Trading REST API（5 端点 + 1 WS）、CLI 子命令
- Then: 多 symbol 持仓聚合正确，API TestClient + WS 双向验证 PASS

### FR-10: Web Dashboard 脚手架 + 鉴权（Phase 3 F 分支）
- Given: 需要 Web 作为用户主要操作入口
- When: 初始化 Vite + React + Tailwind + shadcn/ui 脚手架，实现 JWT 登录 + 401 跳转
- Then: `pnpm dev` 首页可访问，未登录跳 /login

### FR-11: Phase/Backtest/Paper 核心面板（Phase 3 F 分支）
- Given: 用户需要通过 Web 查看 phase、backtest、paper trading
- When: 实现 3 个面板（实时数据 + WS 推送 + 历史曲线/表格）
- Then: 切换 symbol 数据更新，WS 推送 1 秒内刷新，backtest run 状态从 pending→running→success

### FR-12: Alerts/LLMCost/Settings 面板（Phase 3 F 分支）
- Given: 用户需要监控告警、LLM 成本、系统设置
- When: 实现告警中心（确认/静音/桌面通知）、LLM 成本仪表盘（KPI/趋势/缓存命中率）、设置页（主题/时区/语言）
- Then: 数字与 CLI `aegis llm cost` 一致，语言切换全局生效

### FR-13: 全链路集成测试（Phase 4）
- Given: B/D/C/F 全部模块就绪
- When: 编写 5 条端到端链路测试 + 长跑稳定性 + WS 断连重连
- Then: 5 条链路 PASS，4 小时长跑无泄漏，WS 断连重连 10 次不丢消息

### FR-14: 部署 + v0.15.0 发版（Phase 4）
- Given: 所有模块通过验收
- When: 更新 Dockerfile（multi-stage）、docker-compose、文档（USER_GUIDE/CHANGELOG/README），打 tag v0.15.0
- Then: `docker compose up` 一键启动，GitHub Release 发布

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: B 合入后 walk-forward 子命令可用 | `aegis backtest walk-forward --help` 输出正确 |
| AC-2: D 合入后 Prometheus 指标 ≥6 个 | `curl localhost:8000/metrics \| grep aegis_llm_` 输出 ≥6 行 |
| AC-3: B+D 集成冒烟无 ERROR | `aegis analyze --symbol QQQ` 日志无 ERROR |
| AC-4: pytest 0 failed / 0 errors | `pytest tests/ -n auto --tb=short` 输出 0 failed, 0 errors |
| AC-5: ruff 0 errors | `ruff check src/ tests/ web/` 输出 "All checks passed!" |
| AC-6: mypy src/services 0 errors | `mypy src/services` 输出 "Success: no issues found" |
| AC-7: coverage ≥75% | `pytest --cov=src --cov-report=term` 输出 ≥75% |
| AC-8: CI PR 拦截生效 | 故意 lint fail 的 PR 被 GitHub branch protection 拦截 |
| AC-9: pre-commit 正常拦截 | `git commit` 时 ruff/yamllint 自动检查 |
| AC-10: 本地部署 10 项 checklist 全 ✅ | 按 `docs/local-smoke-checklist.md` 逐项打钩 |
| AC-11: PaperBroker 10 个订单生命周期 PASS | `pytest tests/agents/test_paper_broker*.py -v` 10 PASS |
| AC-12: 订单状态机合法性 PASS | `pytest tests/agents/test_paper_broker*.py -v -k state` PASS |
| AC-13: signal→fill→position 端到端 PASS | `pytest tests/integration/test_paper_e2e.py -v` PASS |
| AC-14: Paper API 5 REST + 1 WS 端点验证 | `pytest tests/api/test_paper_route.py -v` PASS |
| AC-15: Web 6 面板可用 | Playwright e2e 6 cases PASS |
| AC-16: Lighthouse ≥80 | Lighthouse CI report Performance ≥80, Accessibility ≥90 |
| AC-17: 端到端 5 条链路 PASS | `pytest tests/integration/test_sprint15_e2e.py -v` 5 PASS |
| AC-18: docker compose up 一键启动 | `docker compose up` 后 `curl localhost:8000/health` 返回 200 |
| AC-19: AGENTS.md 账本完整 | 每个 baseline 条目都有 fix/delete/mock 结论 |
| AC-20: make audit-mocks PASS | `make audit-mocks` 输出 "PASS" |

## 用户故事

- As a 开发者, I want B/D 分支合入 master, So that 后续开发基于完整基线上进行
- As a 开发者, I want 测试全绿 + lint/type 清零, So that CI 可以强阻断，防止新代码引入回归
- As a 量化交易者, I want PaperBroker 模拟交易闭环, So that 可以在不接入真实券商的情况下验证策略
- As a 量化交易者, I want Web Dashboard 6 面板, So that 可以通过浏览器查看 phase/backtest/paper/alerts/llm-cost
- As a 运维者, I want docker compose up 一键启动, So that 部署不依赖复杂的手动配置

## 非功能需求

### NFR-1: 性能
- 全量测试 ≤60s（unit + integration）
- PaperBroker 撮合延迟 <10ms per order
- Web 首屏加载 <3s（Lighthouse Performance ≥80）
- 单进程内存 <4GB

### NFR-2: 可靠性
- CI 强阻断：PR 必须全绿才允许 merge
- pre-commit 自动拦截 lint/format 问题
- WS 断连重连不丢消息
- 4 小时长跑无内存/FD 泄漏

### NFR-3: 可维护性
- 每个 task 独立 commit，message body 引用 task ID
- AGENTS.md 历史失败用例账本完整
- mock 必须配 `# TODO(real-data): ...` 注释
- 测试分块：unit/integration/e2e/slow 四档

### NFR-4: 兼容性
- B(backtest v3) 和 D(LLM 治理) 能力 0 回归
- CLI 保留但降级为 dev/ops 工具
- 不引入新依赖（除已在 plan 中列出的）

## 边界场景

### Edge-1: B/D 合入冲突
- 若 rebase 时发现 conflict，立即停下来 sync，conflict 是设计问题不是 merge 问题

### Edge-2: Phase 1 超时
- Day 6 末硬卡门控，未达标砍 Phase 3 部分能力（F6/F7 推迟）

### Edge-3: Coverage 75% 达不到
- H8 warn 不 block，留 Sprint 16 升 block；但必须有 baseline 数据

### Edge-4: 端到端测试发现深层 bug
- I1 留 2 天缓冲，优先修 critical，info 级问题入 Sprint 16

### Edge-5: Web 与后端 schema 不一致
- F3-F7 每个面板启动前先 mock API，再切真实 API

### Edge-6: 测试超时
- 任何用例 >30s 强制 fail（e2e 60s，slow 显式 opt-in），长流程必须拆成独立子用例

## 回滚计划
- B/D 合入失败：`git reset --hard` 回到合入前 commit
- Phase 1 破坏现有功能：`git revert` 对应 commit
- C/F 接线异常：revert 对应 commit，保留模块独立可用
- 整体回退：切回 master @ `af07882`，保留 `.specs/` 产物

## 数据/权限影响
- 新增 SQLite 表：paper_orders、paper_positions、paper_portfolio_snapshots
- 新增 alembic migration
- 新增 API 端点需 JWT 鉴权（/api/paper/reset 需 admin 角色）
- 新增 Prometheus 指标：aegis_position_mismatch_total

## Alternatives Considered
- **方案 A**: 分 4 个独立分支开发再合入 → 拒绝，集成冲突风险高，B/D 已证明分支独立开发后合入困难
- **方案 B**: 跳过 Hardening 直接开发 C/F → 拒绝，脏基线上加新代码会导致 Hardening 工作量翻倍
- **方案 C**: 先做 C/F 再做 Hardening → 拒绝，Phase 1 不达标禁止进 Phase 2 是核心纪律

## Migration Plan
- Phase 0: B/D rebase 到 master，无数据迁移
- Phase 1: 无数据迁移，仅代码修复
- Phase 2: alembic migration 新增 paper_trading 表
- Phase 3: 无数据迁移，前端静态文件
- Phase 4: Docker 镜像更新，docker-compose 扩展

## Observability
- Prometheus 指标：aegis_llm_*（D 已交付）、aegis_position_mismatch_total（C 新增）
- 日志：DataHarvester 节假日跳过日志、StrategyExec lot_size/price_limit 日志
- CI：GitHub Actions workflow 结果
- Lighthouse：Web 性能报告

## 排除范围（Out of Scope）
- CN/HK 市场支持（E 分支已废弃）
- 真实券商接入（Sprint 16+）
- Telegram Bot（Sprint 16+）
- Polymarket / X 博主（backlog）
- mypy strict 扩展到 src/services 以外模块
- CLI 功能增强（降级为 dev/ops 工具）
- SymbolPicker 调 normalizer API（改本地正则校验）

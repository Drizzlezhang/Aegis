# Requirements: sprint15-hotfix-v0.15.1

<!-- size:all -->
## 功能需求

### FR-1 (P0-1): LLM 治理链补完 + Budget 异常不被吞
- Given: LLM 治理链 `get_governance_chain()` 当前只装配 Execute + Metrics 两层
- When: 修复后调用 `get_governance_chain()`
- Then: 按 Cache → RateLimit → Budget → Execute → Metrics 顺序注册全部 5 层；Budget 超预算时 `BudgetExceededError` 不被 try/except 吞掉，而是向上传播

### FR-2 (P0-2): EventBus 启动 + PositionMonitor 真正消费 OrderFilled
- Given: EventBus 无任何模块在生产路径上 `start()`，PositionMonitor 只打日志不更新状态
- When: FastAPI lifespan 启动时 `await bus.start()`，CLI paper-loop 入口同样启动；PositionMonitor 收到 OrderFilledEvent
- Then: 事件被正确派发；PositionMonitor 更新自身持仓视图，与 PaperBroker 做一致性校验，偏差时 publish AlertEvent

### FR-3 (P0-3): Paper API 鉴权 + 去 module-level 全局 + WS 端点
- Given: 6 个 paper 端点无鉴权，broker/portfolio 是模块级单例
- When: 所有 `/paper/*` 路由强制依赖 `verify_paper_token`；broker/portfolio 放入 `app.state`；新增 WS 端点 `/paper/stream`
- Then: 无 token 返回 401；多 worker 下状态一致（或显式标注单 worker 限制）；WS 推送 Order* 事件

### FR-4 (P0-4): Sprint 16 宪法 grep guard 对齐
- Given: PaperBroker 方法名 `place_order`/`cancel_order` 命中 Sprint 16 宪法 grep guard
- When: 路线 A — 宪法文档限定 grep 范围为 `src/integrations/brokers_external/`，Paper sandbox 例外
- Then: `grep -rE "place_order|submit_order|modify_order|cancel_order" src/ --include="*.py" | grep -v "src/agents/strategy_exec/brokers/"` 输出空

### FR-5 (P1-1): PaperBroker SQLite 持久化
- Given: PaperBroker 只有内存 dict，重启丢失
- When: 每次状态变更同步写 SQLite，启动时从库 reload
- Then: 重启后订单/持仓/权益曲线完整还原

### FR-6 (P1-2): PaperBroker 部分成交
- Given: `_fill_order` 总是 `fill_qty=quantity`
- When: 根据模拟流动性给 0~quantity 的实际成交量
- Then: 剩余 quantity > 0 时状态为 PARTIALLY_FILLED，挂回订单簿等下一 tick

### FR-7 (P1-3): PaperBroker STOP 单
- Given: `place_order` 只处理 MARKET/LIMIT
- When: 加 STOP 分支，价格触及 stop_price 时转为市价
- Then: STOP 单正确触发并走 `_fill_order`

### FR-8 (P1-4): PaperBroker 价格簿不再硬编码
- Given: 14 个 symbol 硬编码价格，其它一律 $100.00
- When: 接入 DataService 拉最新 quote，失败时退到带噪音的缓存
- Then: 任意 ticker 返回非 100.0 的真实/缓存价格

### FR-9 (P1-5): PortfolioService 持久化不再整文件 rewrite
- Given: `_save_history` 每次 snapshot 都 `write_text(json.dumps(...))`
- When: 改成 SQLite INSERT，旧 JSON 一次性迁移
- Then: 1000 次 snapshot 磁盘 IO 下降至少 10×

### FR-10 (P1-6): Web Phase 面板从占位补成真实功能
- Given: `/phase` 只有 8 个 ticker 价格 + "暂无活跃信号"
- When: 实现 SymbolPicker + PhaseCurrentCard + PhaseHistory + usePhaseStream(WS)
- Then: 后端 publish PhaseEvent 后前端实时刷新

### FR-11 (P1-7): 所有 Web 面板真正接 WS
- Given: `useWebSocket` hook 存在但无任何页面调用
- When: Paper/Alerts/LLM-cost 面板订阅对应 WS 端点
- Then: 下单后 1 秒内前端看到新订单行，无需刷新页面

### FR-12 (P1-8): LLM 模块导出 Middleware 类
- Given: CacheMiddleware/RateLimitMiddleware/BudgetMiddleware 未在 `__all__` 导出
- When: 在 `src/llm/__init__.py` 加导出
- Then: 外部代码可按需重装配链路

### FR-13: 指标静默下调回收
- Given: ruff 6 errors，测试基线不一致，覆盖率 25% vs 文档 75%
- When: 跑 ruff fix，对齐测试基线，补测试到 ≥ 40%
- Then: ruff 0 errors，测试基线准确，覆盖率 ≥ 40%

### FR-14: 文档同步
- Given: USER_GUIDE、coverage-baseline、llm-governance 口径过时
- When: P0+P1 全部完成后一次性更新
- Then: 所有文档反映实际状态

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 治理链默认 5 层，Budget 异常不被吞 | `pytest tests/llm/test_middleware_chain.py -v` 全绿（4 个测试） |
| AC-2: EventBus 在 lifespan 启动，PositionMonitor 消费事件 | `pytest tests/integration/test_event_bus_lifecycle.py -v` 全绿（3 个测试） |
| AC-3: Paper API 鉴权生效，WS 端点可用 | `pytest tests/api/test_paper_auth.py tests/api/test_paper_ws.py -v` 全绿（4 个测试） |
| AC-4: 宪法 grep guard 白名单生效 | `grep -rE "place_order\|submit_order\|modify_order\|cancel_order" src/ --include="*.py" \| grep -v "src/agents/strategy_exec/brokers/"` 输出空 + `pytest tests/governance/test_constitution_guard.py` 全绿 |
| AC-5: PaperBroker SQLite 持久化 | `pytest tests/brokers/test_paper_persistence.py -v` 全绿 |
| AC-6: PaperBroker 部分成交 | `pytest tests/brokers/test_paper_partial_fill.py -v` 全绿 |
| AC-7: PaperBroker STOP 单 | `pytest tests/brokers/test_paper_stop_order.py -v` 全绿 |
| AC-8: 价格簿接入 DataService | 手工验证 `_get_simulated_price("MSFT")` 返回非 100.0 |
| AC-9: PortfolioService SQLite 持久化 | `tests/perf/` 脚本压测 IO 下降 ≥ 10× |
| AC-10: Phase 面板实时刷新 | Playwright e2e: `test_phase_panel_renders_phase_event_via_ws` |
| AC-11: Web 面板 WS 实时刷新 | 手工 smoke：下单后 1 秒内前端看到新订单行 |
| AC-12: LLM 模块导出完整 | `python -c "from src.llm import CacheMiddleware, RateLimitMiddleware, BudgetMiddleware, GovernanceAbortError"` 不报错 |
| AC-13: ruff 0 errors | `ruff check src/ tests/` 输出 `All checks passed!` |
| AC-14: 测试基线对齐 | `pytest --collect-only -q \| tail -1` 取真实值，更新 `.audit/test-baseline.txt` |
| AC-15: 覆盖率 ≥ 40% | `pytest --cov=src --cov-report=term` 覆盖率 ≥ 40% |
| AC-16: 手工 smoke 全部通过 | 启动 API+Web，配置 token，下单 → Web 实时刷新 → PositionMonitor 日志正常 → Budget 超限抛异常 |
| AC-17: 文档同步完成 | 检查 USER_GUIDE.md / coverage-baseline.md / llm-governance.md / sprint15-hotfix-v0.15.1.md 内容正确 |
<!-- /size:all -->

<!-- size:S+ -->
## 用户故事
- As a 系统运维者, I want LLM 治理链完整生效, So that 超预算时 LLM 调用被阻止而非静默放行
- As a 策略开发者, I want EventBus 在生产环境正确启动, So that OrderFilled 事件能被 PositionMonitor 消费并触发告警
- As a 安全审计者, I want Paper API 有鉴权保护, So that 暴露端口后不会被未授权下单/清户
- As a Sprint 16 开发者, I want 宪法 grep guard 不误伤 PaperBroker, So that Sprint 16 Phase 0 可以正常启动
- As a 量化交易者, I want PaperBroker 支持持久化/部分成交/STOP 单, So that 模拟交易更接近真实环境
- As a 前端用户, I want Web 面板通过 WS 实时刷新, So that 不需要手动刷新页面就能看到最新状态
<!-- /size:S+ -->

<!-- size:M+ -->
## 非功能需求
### NFR-1: 性能 — PortfolioService IO 下降 ≥ 10×
1000 次 `record_snapshot()` 磁盘 IO 总字节数比旧 JSON rewrite 实现下降至少 10×

### NFR-2: 安全 — Paper API 强制鉴权
所有 `/paper/*` 路由必须依赖 `verify_paper_token`，无 token 返回 401，错误 token 返回 403

### NFR-3: 可靠性 — EventBus 生命周期
FastAPI lifespan 启动时 `await bus.start()`，关闭时 `await bus.stop()`，确保事件不丢失

### NFR-4: 兼容性 — 宪法 grep guard
`grep -rE "place_order|submit_order|modify_order|cancel_order" src/ --include="*.py" | grep -v "src/agents/strategy_exec/brokers/"` 输出空

## 边界场景
### Edge-1: 多 worker 部署下 broker 状态共享
若无法做到跨进程共享，显式在文档中标注"paper trading 当前仅支持单 worker"，并在 app startup 处 worker 数 > 1 时打 ERROR 日志

### Edge-2: DataService 不可用时价格簿回退
`_get_simulated_price` 在 DataService 失败时退到带噪音的 last-known-price 缓存，不返回 $100.00

### Edge-3: 旧 JSON 文件迁移
PortfolioService 启动时若发现 `equity_curve.json`，导入到 SQLite 后重命名为 `equity_curve.json.migrated`

### Edge-4: WS 断线自动重连
`useWebSocket` hook 内置 exponential backoff 重连逻辑

### Edge-5: Budget 调成 0 时 LLM 调用行为
手工 smoke：把 daily budget 调成 0.001 USD，跑一次 debate，期望抛 `BudgetExceededError` 而不是返回 LLM 结果

## 回滚计划
- 每个 P0/P1 子项独立 commit，出问题可单独 revert
- 不 squash 已有 36 个 commit，新提交追加在末尾
- 若 P0-4 路线 A 被否决，可切换到路线 B（重命名方法）

## 数据/权限影响
- 新增 SQLite 文件 `~/.aegis-trader/paper_state.sqlite`（PaperBroker + PortfolioService 共用）
- 新增环境变量 `AEGIS_PAPER_TOKEN`（Paper API 鉴权）
- 旧 `equity_curve.json` 迁移后重命名为 `.migrated`
<!-- /size:M+ -->

<!-- size:L -->
## Alternatives Considered
### P0-4 宪法对齐
- **路线 A（推荐）**：宪法文档限定 grep 范围为 `src/integrations/brokers_external/`，Paper sandbox 例外。工作量小，语义清晰。
- **路线 B**：重命名 PaperBroker 方法为 `submit_paper_order`/`cancel_paper_order`。工作量更大但语义最清晰。需同步改全部调用方（API、CLI、Web、测试）和 BrokerBase 抽象方法。

### 多 worker broker 状态共享
- **方案 A**：引入 Redis 共享状态。本 hotfix 不应扩范围，默认标注"仅支持单 worker"。
- **方案 B**：使用 PostgreSQL 等外部存储。同样超出 hotfix 范围。

## Migration Plan
1. 从 `sprint15-final-integration` 拉 `sprint15-hotfix-v0.15.1` 分支
2. 按 P0-1 → P0-2 → P0-3/P0-4 顺序串行修复
3. P1 子项在 P0 全部 merged 后并行推进
4. 文档同步在 P0+P1 全部完成后一次性更新
5. 打 tag `v0.15.1`

## Observability
- EventBus 启动/停止日志
- PositionMonitor 持仓一致性校验日志（含 drift 告警）
- Paper API 鉴权失败日志（401/403）
- Budget 超限日志（BudgetExceededError）
- WS 连接/断开日志

## 排除范围（Out of Scope）
- 多 worker 跨进程 broker 状态共享（需 Redis，标注为已知限制）
- 真实券商适配层（Sprint 16 范围）
- 覆盖率补到 75%（Sprint 16 H 系列继续补）
- Cypress/Playwright 完整 e2e 测试套件（仅补 Phase 面板一条）
<!-- /size:L -->

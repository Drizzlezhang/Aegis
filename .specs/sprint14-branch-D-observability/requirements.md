# Requirements: sprint14-branch-D-observability

## 功能需求

### FR-1: 修复 chromadb 缺失导致的测试收集失败 (D1)
- Given: CI 环境未安装 `chromadb`（memory extra）
- When: pytest 收集测试时遇到 `tests/agents/test_vector_store.py`
- Then: 测试被优雅跳过（SKIP），不产生 collection error
- 验证方式: `pytest --collect-only tests/agents/test_vector_store.py` 在未安装 chromadb 时返回 SKIP 而非 ERROR

### FR-2: 修复 test_position_lifecycle.py 同名冲突 (D2)
- Given: `tests/e2e/test_position_lifecycle.py` 与 `tests/integration/test_position_lifecycle.py` 同名
- When: pytest 收集测试
- Then: 无 collection conflict 警告
- 验证方式: `pytest --collect-only tests/` 无 "conflict" 警告

### FR-3: 结构化事件总线 (D3)
- Given: 系统运行中
- When: 任意组件调用 `event_bus.publish(event)`
- Then: 所有订阅该事件类型的 handler 被异步调用，一个 handler 抛错不影响其他
- 验证方式: 发布 10 条事件，订阅者收到全部；handler 抛错时其他订阅者仍正常收到事件

### FR-4: 告警规则引擎 (D4)
- Given: 配置了告警规则 YAML
- When: EventBus 发布匹配规则的事件
- Then: 命中规则后通过 TelegramNotifier 发送通知；cooldown 期内重复事件不二次触发
- 验证方式: mock 事件流，规则命中后通知函数被调用；cooldown 期内重复事件不二次触发

### FR-5: Prometheus 指标导出 (D5)
- Given: 服务运行中
- When: 访问 `/metrics` 端点
- Then: 返回 Prometheus 文本格式，包含 >= 10 个 `aegis_*` 指标
- 验证方式: `curl /metrics` 返回 200 + Prometheus 文本格式；`prometheus_client.parser` 可解析

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: pytest --collect-only 0 errors | `pytest --collect-only -q 2>&1` 无 ERROR 行 |
| AC-2: test_vector_store.py 在无 chromadb 时 skip | `pytest --collect-only tests/agents/test_vector_store.py` 显示 SKIPPED |
| AC-3: test_position_lifecycle 无同名冲突 | `pytest --collect-only tests/` 无 "conflict" 警告 |
| AC-4: EventBus pub/sub 正确投递 | `python3 -m pytest tests/services/test_event_bus.py -v` 通过 |
| AC-5: EventBus handler 异常隔离 | 同上测试覆盖 |
| AC-6: Alerting 规则命中 + cooldown | `python3 -m pytest tests/services/test_alerting.py -v` 通过 |
| AC-7: Alerting 规则 YAML schema 校验 | pydantic 模型校验通过 |
| AC-8: /metrics 端点返回 Prometheus 格式 | `python3 -m pytest tests/services/test_metrics.py -v` 通过 |
| AC-9: >= 10 个 aegis_* 指标 | 测试中解析 /metrics 输出，计数 >= 10 |
| AC-10: ruff + mypy 通过 | `ruff check src/services/` + `mypy src/services/` 无新增错误 |
| AC-11: 告警规则文档示例 >= 5 条 | `config/alerting_rules.yaml` 包含 >= 5 条规则 |

## 用户故事

- As a **SRE 工程师**, I want **Prometheus 指标导出**，So that **我可以将 Aegis 接入现有监控基础设施（Grafana dashboard）**
- As a **运维人员**, I want **YAML 可配的告警规则**，So that **phase 置信度异常时 5 分钟内收到 Telegram 通知，无需 grep 日志**
- As a **开发者**, I want **结构化事件总线**，So that **下游分支（Branch A/B/E）可以零侵入订阅事件，不修改业务 Agent 接口**
- As a **CI 维护者**, I want **pytest 收集阶段 0 errors**，So that **CI 流水线不会因可选依赖缺失而误报失败**

## 排除范围（Out of Scope）
- 不引入新通知通道（仅复用 TelegramConfig）
- 不修改业务 Agent 接口（事件订阅模式，发布方零侵入）
- 不实现分布式事件总线（单进程 asyncio.Queue 足够）
- 不实现 Prometheus multi-process mode（当前单 worker）
- 不实现告警规则 Web UI 编辑器

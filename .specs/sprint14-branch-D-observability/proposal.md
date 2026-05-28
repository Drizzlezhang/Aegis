# Change: sprint14-branch-D-observability

## 概述
补齐 Sprint 13 遗留的可观测性短板，建立结构化事件 → 告警 → 通知的完整链路（EventBus + Alerting + Prometheus Metrics），同时修复 2 个测试收集问题。

## 动机
- 当前系统缺乏结构化事件发布/订阅机制，Agent 间通信依赖隐式状态传递
- 无告警能力，phase 异常只能通过 grep 日志发现，MTTR 高
- 无 Prometheus 指标导出，无法接入监控基础设施
- CI 测试收集阶段存在 2 个 errors（chromadb 缺失 + 同名冲突）

## 影响范围
- `pyproject.toml` — optional-dependencies + pytest 配置
- `tests/e2e/test_position_lifecycle.py` → `test_position_lifecycle_e2e.py` — 重命名
- `tests/services/test_vector_store.py` — 顶部加 importorskip
- `src/services/event_bus.py` — 新增，asyncio.Queue pub/sub
- `src/services/alerting.py` — 新增，YAML 规则引擎
- `src/services/metrics.py` — 新增，Prometheus 指标
- `src/api/metrics_routes.py` — 新增 /metrics 端点
- `src/config.py` — 新增 AlertingConfig / MetricsConfig
- `config/alerting_rules.yaml` — 新增示例规则
- `tests/services/test_event_bus.py` — 新增
- `tests/services/test_alerting.py` — 新增
- `tests/services/test_metrics.py` — 新增

## 验收目标
- pytest --collect-only 0 errors
- 新增 ~10 tests
- ruff + mypy 通过
- 告警规则 YAML 通过 schema 校验
- /metrics 端点可被 prometheus 抓取
- 告警规则文档示例 >= 5 条

## Size: S
## 推断依据
- 范围：单模块（services），纯增量，不修改业务 Agent 接口
- 关键词：add observability / alerting / metrics
- 预估文件数：~15（含测试）
- 依赖变更：新增 prometheus_client（optional），无破坏性
- 风险：低，事件订阅模式零侵入

## 阶段序列
0 → 1 → 4 → 5 → 6（S 跳过 DESIGN/PLAN）

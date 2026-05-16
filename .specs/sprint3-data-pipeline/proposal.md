# Change: sprint3-data-pipeline

## 概述
生产级数据层加固 + LLM 网关落地 + 配置热更新 + 健康检查 + 数据源容灾。

## 动机
Sprint 1/2 已完成数据管道基础架构（BaseFetcher、DataFetcherManager、LLM 路由/客户端、DataNormalizer）。Sprint 3 需将系统从 "可用" 推进到 "可生产"：配置热重载、LLM 网关统一入口、多 fetcher 自动降级、子系统健康检查、成本感知路由。

## 影响范围
- `src/config.py` — ConfigProfile + reload_config()
- `src/llm/gateway.py` — 新增 LLMGateway 统一入口
- `src/llm/router.py` — Token 预估 + 成本计算
- `src/agents/data_harvester/fetcher_manager.py` — Fallback chain + FetcherMetrics
- `src/agents/data_harvester/health.py` — 新增 HealthStatus 聚合
- `skills/data_sources/` — 容灾支持
- `tests/` — 18 个新增测试

## 验收目标
- 配置热重载线程安全，Profile 切换生效
- LLMGateway 记录所有请求/错误/延迟指标
- DataFetcherManager 熔断后自动降级到次优先级 fetcher
- HealthStatus 聚合 fetcher + LLM provider 状态
- LLMRouter 支持成本上限路由决策
- 401 测试全绿

## Size: M
## 推断依据
- 范围: 5 模块（config, llm, data_harvester, skills, tests），7 文件新增/修改
- 预估文件数: 10-20
- 依赖变更: 内部模块交互，无新增外部依赖
- 风险: 中等 — Gateway 为可选包装，不破坏现有 LLMClient 调用

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

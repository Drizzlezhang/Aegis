# Change: sprint15-branch-D-llm-cost-governance

## 概述
建立 LLM 调用全链路成本治理体系：统一中间件、Token 计量、Prompt 缓存、Rate Limiter、Budget Guard、Prompt 模板版本化、Cost Dashboard CLI、Cost API、文档与告警规则。

## 动机
当前 `debate` / `report_generator` / `quant_brain` 等 Agent 大量调用 LLM，但**没有 token 统计、没有缓存、没有 rate limit、没有 budget 阻断**。本分支建立 LLM 调用全链路成本治理体系。

## 影响范围
- 新增治理模块：`src/llm/middleware.py`, `pricing.py`, `cache.py`, `rate_limiter.py`, `budget.py`, `registry.py`
- Prompt 模板重组：`src/llm/prompts/*.yaml`
- 新增 API：`src/api/routes/llm.py`
- 修改现有：`src/observability/metrics.py`, `src/config.py`, `src/cli.py`
- 数据库：新增 `llm_call_log` 表 (Alembic migration)
- 配置：`config/alerting_rules.yaml` 扩展 4 条规则
- 测试：7 个新测试文件，~12 新测试
- 文档：`docs/llm-governance.md`

## 验收目标
- [ ] 同 prompt 二次调用 cache hit (latency <10ms)
- [ ] daily budget 80%/100% 双告警 + 阻断生效
- [ ] `/api/llm/usage` 数据准确性 (与 SQLite 直查对账)
- [ ] Prometheus 指标 ≥6 个 `aegis_llm_*`
- [ ] ~12 新测试 PASS
- [ ] cache 命中率 (debate 场景跑一次) ≥ 30%

## Size: M
## 推断依据
- 范围：跨模块（llm, api, observability, config, cli, db），涉及 ~20+ 文件
- 关键词：feature（新功能开发）
- 预估文件数：~20-30
- 依赖变更：无新增外部依赖（tiktoken 已是依赖）
- 风险：需回归测试，中间件链接入可能破坏现有 LLM 调用行为
- project.yaml scale: L，但本变更范围限定在 LLM 治理子域，实际为 M

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

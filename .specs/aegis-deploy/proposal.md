# Change: aegis-deploy

## 概述
提升部署健壮性：增加启动时环境配置验证、优雅关停机制、前端 health check，完善 Docker 配置。

## 动机
当前系统缺少启动时的配置完整性检查（如 JWT secret 未设置、LLM API key 缺失），关停流程不完整（scheduler 未优雅停止、positions 未持久化），Docker 部署缺少 health check 和日志轮转配置。这些问题在生产环境中会导致不可预期的行为。

## 影响范围
- `src/config.py` — 新增 `model_validator` 验证 critical secrets
- `src/api/main.py` — 增强 lifespan shutdown 逻辑（scheduler stop、WS close、positions save）
- `web/app/api/health/route.ts` — 新建前端 health check endpoint
- `docker-compose.yml` — 增加 healthcheck、logging、depends_on
- `Dockerfile` — 增加 HEALTHCHECK 指令
- `.env.example` — 新建环境变量模板
- `tests/test_config_validation.py` — 新建配置验证测试
- `tests/api/test_health.py` — 扩展 health/shutdown 测试

## 验收目标
| # | 条件 |
|---|---|
| 1 | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` 0 failed |
| 2 | `cd web && npx tsc --noEmit` 0 errors |
| 3 | 缺少 JWT secret 时启动有 warning 日志但不 crash |
| 4 | `AEGIS_STRICT_VALIDATION=true` + 缺少 secret → 启动失败 |
| 5 | SIGTERM 发送后，scheduler 停止 + positions 保存 + 进程退出 |
| 6 | `GET /api/health` (frontend) 返回 backend 连通状态 |
| 7 | docker-compose frontend 有 healthcheck 且 depends_on backend |
| 8 | `.env.example` 包含所有 env vars 及注释 |
| 9 | 新增 ≥4 tests |

## Size: M
## 推断依据
- 范围：跨模块（config + API + Docker + 前端），~7 文件
- 关键词：`deploy`、`startup validation`、`graceful shutdown`、`health check` — 部署健壮性新功能
- 预估文件数：7（含新建 3 个）
- 依赖变更：仅内部
- 风险：中等 — 改动 startup/shutdown 生命周期，需回归测试

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

# Change: sprint5-infra

## 概述
补齐生产基础设施：JWT Auth + PostgreSQL + Rate Limit + Docker Compose + CI 增强。

## 动机
当前 Aegis 交易系统缺少生产环境必需的基础设施：无认证机制、数据库停留在 SQLite 单机模式、无限流保护、无容器编排、CI 未覆盖前端。本次变更补齐这些能力，且 Auth 默认关闭、DB 默认 SQLite，不破坏现有开发体验。

## 影响范围
| 模块 | 文件 | 操作 |
|------|------|------|
| config | `src/config.py` | 修改 — 新增 AuthConfig + DatabaseConfig |
| database | `src/db.py` | 新建 — SQLAlchemy async 引擎管理 |
| migrations | `alembic/` | 新建 — 初始 migration（decisions/positions/execution_history） |
| middleware | `src/api/middleware/auth.py` | 新建 — JWT + API Key 中间件 |
| middleware | `src/api/middleware/rate_limit.py` | 新建 — Token bucket 限流 |
| routes | `src/api/routes/auth.py` | 新建 — /api/auth/login 路由 |
| API | `src/api/main.py` | 修改 — 注册 middleware + router |
| deploy | `deploy/docker-compose.yml` | 新建 — PostgreSQL + Redis + API + Web |
| CI | `.github/workflows/ci.yml` | 修改 — 新增前端 tsc + build job |
| tests | `tests/api/test_auth_middleware.py` | 新建 — 4 tests |
| tests | `tests/api/test_rate_limit.py` | 新建 — 2 tests |
| tests | `tests/api/test_auth_routes.py` | 新建 — 2 tests |
| config | `.env.example` | 修改 — 补充 JWT/CORS 说明 |

## 验收目标
- [ ] AuthConfig + DatabaseConfig 正确加载
- [ ] Auth 中间件正确拦截/放行（JWT Bearer / API Key / Public Path / WebSocket）
- [ ] Rate Limit 中间件在配额内放行、超配额返回 429
- [ ] /api/auth/login 用 API Key 换取 JWT Token
- [ ] SQLAlchemy async engine 兼容 SQLite + PostgreSQL
- [ ] Alembic migration 可创建 3 张表
- [ ] Docker Compose 可启动全部服务
- [ ] CI 前端 job 与后端 job 并行
- [ ] 8 个新增测试全部通过
- [ ] 现有测试套件无回归

## Size: M
## 推断依据
- 范围：跨 7 个模块/领域（config, db, middleware, routes, alembic, deploy, CI, tests）
- 关键词：feat, infra, new features
- 预估文件数：12-15
- 依赖变更：新增外部依赖（alembic, asyncpg, aiosqlite, PyJWT）
- 风险：中 — Auth 默认关闭、DB 默认 SQLite，不破坏现有开发体验

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（M 全流程，包含 post-spec gate）
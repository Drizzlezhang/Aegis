# Design: sprint5-infra

## 技术方案概述

在现有 FastAPI + Pydantic Settings 架构上，新增认证、数据库、限流三层基础设施。遵循现有模式：`BaseModel` 嵌套配置 → `Config(BaseSettings)` 主类 → 全局单例。中间件按 Starlette `BaseHTTPMiddleware` 规范，DB 引擎用 lazy singleton。所有新增能力默认关闭或向下兼容。

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| AuthConfig | `src/config.py` | 认证相关配置（JWT/API Key/CORS），默认 `enabled=False` |
| DatabaseConfig | `src/config.py` | DB 连接配置，默认 SQLite |
| DB Engine | `src/db.py` | SQLAlchemy async engine + session 管理，全局单例 |
| Alembic | `alembic/` | DB migration 骨架，初始包含 3 张表 |
| AuthMiddleware | `src/api/middleware/auth.py` | JWT Bearer + API Key + WebSocket token 认证 |
| RateLimitMiddleware | `src/api/middleware/rate_limit.py` | 基于 IP 的 token bucket 限流 |
| Auth Routes | `src/api/routes/auth.py` | `/api/auth/login` — API Key → JWT 交换 |
| Docker Compose | `deploy/docker-compose.yml` | PostgreSQL 16 + Redis 7 + API(8001) + Web(3000) |
| CI Frontend | `.github/workflows/ci.yml` | 新增 parallel frontend job（tsc + build） |

## API 设计

### POST /api/auth/login
- **Request**: `{"api_key": "<key>"}`
- **Response 200**: `{"access_token": "<jwt>", "token_type": "bearer", "expires_in": <seconds>}`
- **Response 401**: `{"detail": "Invalid API key"}`
- **Auth**: 无（公开路径，由 AuthMiddleware 放行）

### 认证方式优先级
1. **X-API-Key header** → 匹配 `api_keys` 列表则放行
2. **Authorization: Bearer <jwt>** → JWT decode + exp 校验
3. **WebSocket /ws/*** → query param `?token=<jwt>`
4. 以上均失败 → **401**

### 公开路径（无需认证）
`/api/health`, `/api/auth/login`, `/docs`, `/openapi.json`

### Rate Limit 错误响应
- **429**: `{"detail": "Rate limit exceeded"}`

## 数据模型

### decisions 表
| 列 | 类型 | 约束 |
|----|------|------|
| id | UUID | PK |
| symbol | VARCHAR | NOT NULL |
| action | VARCHAR | NOT NULL |
| strategy_type | VARCHAR | NOT NULL |
| confidence | FLOAT | NOT NULL |
| entry_price | FLOAT | NOT NULL |
| target_pct | FLOAT | NOT NULL |
| stop_loss_pct | FLOAT | NOT NULL |
| reasoning | TEXT | |
| score | FLOAT | nullable |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### positions 表
| 列 | 类型 | 约束 |
|----|------|------|
| id | UUID | PK |
| symbol | VARCHAR | NOT NULL |
| position_type | VARCHAR | NOT NULL |
| entry_price | FLOAT | NOT NULL |
| current_price | FLOAT | NOT NULL |
| quantity | INTEGER | NOT NULL |
| status | VARCHAR | NOT NULL (active/closed/expired/rolled) |
| entry_date | TIMESTAMP | NOT NULL |
| exit_date | TIMESTAMP | nullable |
| exit_price | FLOAT | nullable |
| pnl | FLOAT | nullable |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### execution_history 表
| 列 | 类型 | 约束 |
|----|------|------|
| id | UUID | PK |
| symbol | VARCHAR | NOT NULL |
| pipeline_run_id | VARCHAR | NOT NULL |
| execution_time_s | FLOAT | NOT NULL |
| agent_sequence | JSON | NOT NULL |
| recommendations_count | INTEGER | NOT NULL |
| success | BOOLEAN | NOT NULL |
| created_at | TIMESTAMP | NOT NULL |

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Auth 中间件与现有 lifespan 初始化冲突 | API 启动失败 | Auth 默认 disabled，不影响启动；middleware 依赖注入最小化 |
| 新增依赖与现有 `pyproject.toml` extras 冲突 | 安装失败 | 仅在 `[dev]` extras 中添加 alembic/aiosqlite/asyncpg/PyJWT |
| Rate Limit 中间件内存泄漏（IP 无限增长） | OOM | 定期清理过期 bucket（> 5min 未活跃则移除） |
| Docker Compose 端口与现有 Dockerfile 不一致 | 服务发现失败 | 统一使用 8001（与 Dockerfile HEALTHCHECK 一致） |
| CI 前端 job 缺少 npm cache 路径 | CI 慢 | 使用 `actions/setup-node@v4` 内置 cache + `cache-dependency-path` |

## 回滚计划
1. 从 `src/api/main.py` 移除 `AuthMiddleware` 和 `RateLimitMiddleware` 注册行
2. 回退 `src/config.py` 中 AuthConfig / DatabaseConfig 和 Config 类中的两行字段声明
3. 删除 `alembic/` 目录和 `src/db.py`
4. 移除 `deploy/docker-compose.yml`
5. 回退 `.github/workflows/ci.yml` 新增的 frontend job
6. 回退 `.env.example` 新增的 Auth/DB 配置段
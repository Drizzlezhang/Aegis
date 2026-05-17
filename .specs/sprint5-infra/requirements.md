# Requirements: sprint5-infra

## 功能需求

### FR-1: AuthConfig — 认证配置
- Given: 系统启动加载配置
- When: 读取环境变量中的 JWT / API Key / CORS 相关字段
- Then: AuthConfig 正确解析 `enabled`, `jwt_secret`, `jwt_algorithm`, `access_token_expire_minutes`, `api_key_header`, `api_keys`, `cors_origins`

### FR-2: DatabaseConfig — 数据库配置
- Given: 系统启动加载配置
- When: 读取环境变量中的数据库连接字段
- Then: DatabaseConfig 正确解析 `url`（默认 SQLite）、`pool_size`、`max_overflow`、`echo`

### FR-3: Database Engine — 异步引擎管理
- Given: 系统调用 `get_session()` 或 `get_engine()`
- When: 首次访问时根据配置创建 engine
- Then: SQLite URL 自动转为 `sqlite+aiosqlite:///`，PostgreSQL URL 自动转为 `postgresql+asyncpg://`，engine 全局复用

### FR-4: Alembic 初始迁移
- Given: 执行 `alembic upgrade head`
- When: 运行初始 migration
- Then: 创建 `decisions`（15 列含 UUID PK + reasoning TEXT）、`positions`（14 列含 status 枚举 + pnl）、`execution_history`（8 列含 agent_sequence JSON）3 张表

### FR-5: JWT Auth 中间件
- Given: 请求到达 API
- When: `auth.enabled = True` 时
- Then: `/api/health`, `/api/auth/login`, `/docs`, `/openapi.json` 直接放行；`/ws/*` 从 query param 取 token 验证；其他路径依次尝试 X-API-Key → JWT Bearer → 401

### FR-6: Auth API Route
- Given: 客户端持有有效 API Key
- When: `POST /api/auth/login` 携带 `{"api_key": "<key>"}`
- Then: 返回 `{"access_token": "<jwt>", "token_type": "bearer", "expires_in": <seconds>}`

### FR-7: Rate Limit 中间件
- Given: 同一 IP 在 60s 窗口内发送请求
- When: 请求数超过 rate（默认 120 req/60s）
- Then: 返回 429 `{"detail": "Rate limit exceeded"}`

### FR-8: Docker Compose 编排
- Given: 执行 `docker compose up`
- When: 所有服务健康检查通过
- Then: aegis-api (8003)、aegis-web (3000)、postgres (5432)、redis (6379) 全部可用，API 连接 PostgreSQL

### FR-9: CI 前端增强
- Given: PR 推送到 GitHub
- When: CI workflow 触发
- Then: 前端 job（tsc --noEmit + npm run build）与后端 job 并行执行

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: AuthConfig 字段完整加载，默认 `enabled=False` | 单元测试：`python -c "from src.config import get_config; c=get_config(); assert c.auth.enabled is False"` |
| AC-2: DatabaseConfig 默认 URL 为 SQLite | 单元测试：`python -c "from src.config import get_config; c=get_config(); assert 'sqlite' in c.database.url"` |
| AC-3: src/db.py engine 创建支持 SQLite async | `python -m py_compile src/db.py` 通过 + 集成测试连接内存 SQLite |
| AC-4: Alembic upgrade 创建 3 张表 | `alembic upgrade head` 后检查 SQLite 中 `decisions`, `positions`, `execution_history` 表存在 |
| AC-5: Auth 中间件 — 公开路径放行 | test_public_path_no_auth |
| AC-6: Auth 中间件 — 有效 JWT 通过 | test_valid_jwt_passes |
| AC-7: Auth 中间件 — 过期 JWT 拒绝 | test_expired_jwt_rejected |
| AC-8: Auth 中间件 — 有效 API Key 通过 | test_valid_api_key_passes |
| AC-9: /api/auth/login — 正确 API Key 返回 JWT | test_login_success |
| AC-10: /api/auth/login — 无效 API Key 返回 401 | test_login_invalid_key |
| AC-11: Rate Limit — 配额内放行 | test_requests_within_limit |
| AC-12: Rate Limit — 超配额返回 429 | test_rate_limit_exceeded |
| AC-13: Docker Compose 服务全部健康 | `docker compose -f deploy/docker-compose.yml up -d && docker compose ps` 全部 healthy |
| AC-14: CI 前端 job 存在且可执行 | 检查 `.github/workflows/ci.yml` 包含 `frontend` job + `tsc --noEmit` + `npm run build` |
| AC-15: 现有测试套件无回归 | `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py` |

## 用户故事

- As a 系统管理员, I want Auth 默认关闭, So that 开发环境不需要额外配置就能正常工作
- As a 前端开发者, I want `/api/auth/login` 用 API Key 换 JWT, So that 前端可以无状态认证
- As a 运维人员, I want Docker Compose 一键启动全部服务, So that 部署不再依赖手动配置
- As a 安全审计, I want Rate Limit 防止 API 滥用, So that 系统不被单 IP 打垮
- As a 数据工程师, I want PostgreSQL 支持, So that 生产环境有可靠的持久化存储

## 非功能需求

### NFR-1: 向后兼容
Auth 默认 disabled，DB 默认 SQLite，现有 workflow 不受影响。

### NFR-2: 配置热加载友好
Config 通过环境变量注入，与 Docker Compose / CI 无缝衔接。

### NFR-3: 性能
Rate Limit 使用纯内存 token bucket，O(1) 每次请求；DB 使用连接池复用。

### NFR-4: 可观测性
DB echo 模式可选开启用于调试；中间件错误返回标准 HTTP 状态码。

## 边界场景

### Edge-1: Auth disabled 时中间件完全透明
所有请求直接通过，不做任何 token 校验。

### Edge-2: WebSocket 认证
`/ws/*` 路径通过 `?token=<jwt>` query param 认证，不依赖 Authorization header。

### Edge-3: API Key 优先级高于 JWT
先检查 X-API-Key header，匹配则直接放行，不检查 JWT。

### Edge-4: 配置缺失时回退默认值
`jwt_secret` 为空时，JWT decode 将失败，不会出现空指针。

### Edge-5: PostgreSQL URL 无需 async 前缀
用户配置 `postgresql://` 即可，engine 自动添加 `+asyncpg`。

### Edge-6: Rate Limit 多实例警告
内存 bucket 单实例有效；多实例部署需额外配置。

## 回滚计划
1. 从 `src/api/main.py` 移除 `AuthMiddleware` 和 `RateLimitMiddleware` 注册
2. 回退 `src/config.py` 中 AuthConfig / DatabaseConfig 新增字段
3. 删除 `alembic/` 目录（如未在生产执行 migration）
4. 移除 `deploy/docker-compose.yml`（不影响现有部署）

## 数据/权限影响
- 新增 3 张 DB 表（decisions, positions, execution_history），无存量数据迁移
- Auth 控制 API 访问权限，默认关闭不影响现有调用方
- `.env.example` 新增 JWT/CORS 字段，需通知开发者更新本地 `.env`
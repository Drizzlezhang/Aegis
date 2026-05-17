# Tasks: sprint5-infra

## 任务波次

### Wave 1 — 基础设施配置（无依赖，可并行）

#### T01: AuthConfig + DatabaseConfig 扩展
- 描述: 在 `src/config.py` 的 `WebConfig` 之后新增 `AuthConfig` 和 `DatabaseConfig`，在 `Config` 主类中添加 `auth` / `database` 字段
- read_files: [src/config.py]
- write_files: [src/config.py]
- verify: `python3 -m py_compile src/config.py && python3 -c "from src.config import get_config; c=get_config(); print(c.auth.enabled, c.database.url)"`
- status: pending

#### T02: Database Engine 管理
- 描述: 新建 `src/db.py`，实现 lazy singleton engine + session factory + `get_session()` context manager，自动适配 SQLite → aiosqlite / PG → asyncpg
- read_files: [src/config.py]
- write_files: [src/db.py]
- verify: `python3 -m py_compile src/db.py`
- status: pending

#### T03: Alembic 初始化 + 初始 Migration
- 描述: 安装 alembic/asyncpg/aiosqlite，初始化 alembic，修改 `env.py` 接入 `src.config`，创建初始 migration（decisions / positions / execution_history 3 张表）
- read_files: [src/config.py, pyproject.toml]
- write_files: [alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/001_initial.py]
- verify: `alembic upgrade head && python3 -c "from src.db import get_engine; from sqlalchemy import inspect; import asyncio; async def chk(): async with get_engine().connect() as c: print(await c.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())); asyncio.run(chk())"`
- status: pending

#### T04: .env.example 更新
- 描述: 替换现有 JWT/CORS/DB 占位注释为 Auth + DB 配置段，补充 `AEGIS_AUTH__*` 和 `AEGIS_DATABASE__*` 环境变量说明
- read_files: [.env.example]
- write_files: [.env.example]
- verify: `grep -c "AEGIS_AUTH__" .env.example && grep -c "AEGIS_DATABASE__" .env.example`
- status: pending

### Wave 2 — 中间件与路由（依赖 T01，可并行）

#### T05: JWT Auth 中间件
- 描述: 新建 `src/api/middleware/__init__.py` + `src/api/middleware/auth.py`，实现 `AuthMiddleware(BaseHTTPMiddleware)`：公开路径放行、WebSocket query param token、API Key → JWT Bearer 三级认证
- depends_on: [T01]
- read_files: [src/config.py, src/api/main.py]
- write_files: [src/api/middleware/__init__.py, src/api/middleware/auth.py]
- verify: `python3 -m py_compile src/api/middleware/auth.py`
- status: pending

#### T06: Rate Limit 中间件
- 描述: 新建 `src/api/middleware/rate_limit.py`，实现 `RateLimitMiddleware(BaseHTTPMiddleware)`：基于 IP 的 token bucket，默认 120 req/60s，含过期 bucket 清理
- depends_on: [T01]
- read_files: [src/api/main.py]
- write_files: [src/api/middleware/rate_limit.py]
- verify: `python3 -m py_compile src/api/middleware/rate_limit.py`
- status: pending

#### T07: Auth API Routes
- 描述: 新建 `src/api/routes/auth.py`，实现 `POST /api/auth/login`（LoginRequest → TokenResponse），API Key 校验 + JWT 签发
- depends_on: [T01]
- read_files: [src/config.py]
- write_files: [src/api/routes/auth.py]
- verify: `python3 -m py_compile src/api/routes/auth.py`
- status: pending

### Wave 3 — API 集成（依赖 T05, T06, T07）

#### T08: 注册中间件与路由
- 描述: 修改 `src/api/main.py` 注册 AuthMiddleware + RateLimitMiddleware，在 `src/api/routes/__init__.py` 添加 auth 导入，在 main.py 注册 auth router
- depends_on: [T05, T06, T07]
- read_files: [src/api/main.py, src/api/routes/__init__.py]
- write_files: [src/api/main.py, src/api/routes/__init__.py]
- verify: `python3 -m py_compile src/api/main.py && python3 -c "from src.api.main import app; print([r.path for r in app.routes])"`
- status: pending

### Wave 4 — 测试（依赖 T08，可并行）

#### T09: Auth Middleware 测试
- 描述: 新建 `tests/api/test_auth_middleware.py`，4 tests：公开路径放行 / 有效 JWT 通过 / 过期 JWT 拒绝 / 有效 API Key 通过
- depends_on: [T08]
- read_files: [src/api/middleware/auth.py, src/api/main.py]
- write_files: [tests/api/test_auth_middleware.py]
- verify: `python -m pytest tests/api/test_auth_middleware.py -x --tb=short`
- status: pending

#### T10: Rate Limit 测试
- 描述: 新建 `tests/api/test_rate_limit.py`，2 tests：配额内放行 / 超配额返回 429
- depends_on: [T08]
- read_files: [src/api/middleware/rate_limit.py, src/api/main.py]
- write_files: [tests/api/test_rate_limit.py]
- verify: `python -m pytest tests/api/test_rate_limit.py -x --tb=short`
- status: pending

#### T11: Auth Routes 测试
- 描述: 新建 `tests/api/test_auth_routes.py`，2 tests：正确 API Key 登录成功 / 无效 API Key 返回 401
- depends_on: [T08]
- read_files: [src/api/routes/auth.py, src/api/main.py]
- write_files: [tests/api/test_auth_routes.py]
- verify: `python -m pytest tests/api/test_auth_routes.py -x --tb=short`
- status: pending

### Wave 5 — 部署与 CI（无代码依赖，可并行）

#### T12: Docker Compose
- 描述: 新建 `deploy/docker-compose.yml`，包含 aegis-api (8001) + aegis-web (3000) + postgres:16 + redis:7，healthcheck + volume + env 注入
- read_files: [Dockerfile, deploy/supervisord.conf]
- write_files: [deploy/docker-compose.yml]
- verify: `docker compose -f deploy/docker-compose.yml config --quiet`
- status: pending

#### T13: CI 前端增强
- 描述: 修改 `.github/workflows/ci.yml`，在现有 test job 后添加并行 frontend job（setup-node + npm ci + tsc --noEmit + npm run build）
- read_files: [.github/workflows/ci.yml]
- write_files: [.github/workflows/ci.yml]
- verify: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML valid')"`
- status: pending

## 风险任务
- **T03 (Alembic)**: 首次 migration 生成需验证 DB 方言兼容性（SQLite vs PG），可能需要手动调整 migration 脚本中的 column types
- **T08 (API 集成)**: 中间件注册顺序影响请求链路，AuthMiddleware 需在 RateLimitMiddleware 之前注册

## 回滚任务
- 每个 wave 完成后 git commit，失败时可以直接 git revert
- T08 集成前，所有新文件不影响现有行为（无 import 路径导入）
- 回滚顺序：T08 → T07/T06/T05 → T03/T02/T01 → T04/T12/T13（与建设顺序相反）
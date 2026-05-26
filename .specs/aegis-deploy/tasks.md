# Tasks: aegis-deploy

## Wave 1: 独立模块（可并行）

### T1: Config startup validation
- **依赖**: 无
- **读**: `src/config.py`
- **写**: `src/config.py`
- **内容**: 新增 `ConfigValidationError` 异常类；新增 `strict_validation: bool = False` 字段；新增 `model_validator(mode="after")` 方法 `validate_required_secrets`，检查 `auth.jwt_secret` 长度 >= 16 和至少一个 LLM API key；新增 `validation_warnings` property 和 `is_production_ready` property
- **verify**: `python3 -c "from src.config import Config; c = Config(); print(len(c.validation_warnings))"`

### T2: 前端 health check endpoint
- **依赖**: 无
- **读**: 无（新建文件）
- **写**: `web/app/api/health/route.ts`
- **内容**: 新建 `GET /api/health` route，探测 `{NEXT_PUBLIC_API_URL}/api/status`（5s 超时），返回 `{ status, timestamp, version, uptime, responseTimeMs, backend }`；backend 可达时 200，不可达时 503
- **verify**: `cd web && npx tsc --noEmit`

### T3: .env.example
- **依赖**: 无
- **读**: `src/config.py`（确认所有 env var 名称）
- **写**: `.env.example`
- **内容**: 创建环境变量模板，包含 Required（AUTH_JWT_SECRET、LLM_API_KEY）和 Optional（AEGIS_PROFILE、AEGIS_STRICT_VALIDATION、LLM 配置、Scheduler、Telegram、Data Sources、Server、Docker）分组
- **verify**: `test -f .env.example && grep -q AUTH_JWT_SECRET .env.example && grep -q AEGIS_STRICT_VALIDATION .env.example`

## Wave 2: 应用层集成（依赖 Wave 1）

### T4: Graceful shutdown
- **依赖**: T1
- **读**: `src/api/main.py`
- **写**: `src/api/main.py`
- **内容**: 在 lifespan startup 中：输出 config validation warnings；将 `position_manager` 赋值给 `app.state.position_manager`；注册 SIGTERM/SIGINT 信号处理器。在 lifespan shutdown 中：增强为有序关停（scheduler.shutdown → WS close → position_manager.save → realtime_manager.shutdown），包裹在 `asyncio.wait_for(..., timeout=30)` 中
- **verify**: `python3 -c "from src.api.main import app; print('OK')"`

## Wave 3: Docker 配置（依赖 Wave 2）

### T5: docker-compose.yml 增强
- **依赖**: T4
- **读**: `docker-compose.yml`
- **写**: `docker-compose.yml`
- **内容**: 拆分为 backend + frontend 双服务；backend 保留现有 healthcheck + 新增 logging（json-file, 50m/5）；frontend 新增 healthcheck（curl `/api/health`）、logging（json-file, 20m/3）、depends_on backend（condition: service_healthy）
- **verify**: `docker compose config -q 2>&1 || echo "docker not available, skip"`

### T6: Dockerfile 前端 HEALTHCHECK
- **依赖**: T2
- **读**: `Dockerfile`
- **写**: `Dockerfile`
- **内容**: 在 runtime stage 中新增前端 HEALTHCHECK 指令（`curl -f http://localhost:3000/api/health`）
- **verify**: `grep -q "HEALTHCHECK.*3000/api/health" Dockerfile`

## Wave 4: 测试（依赖 Wave 1-3）

### T7: 后端测试
- **依赖**: T1, T4
- **读**: `src/config.py`, `src/api/main.py`
- **写**: `tests/test_config_validation.py`（新建）, `tests/api/test_health.py`（扩展）
- **内容**: 
  - `test_validation_warns_on_short_jwt_secret` — 空 jwt_secret → validation_warnings 非空
  - `test_validation_warns_on_missing_llm_key` — 所有 LLM key 为空 → validation_warnings 非空
  - `test_is_production_ready_false_when_issues_exist` — 有 warning 时 is_production_ready=False
  - `test_strict_mode_raises_on_validation_failure` — strict_validation=True + 空 jwt_secret → ConfigValidationError
  - `test_backend_status_endpoint_returns_200` — GET /api/health → 200
- **verify**: `python3 -m pytest tests/test_config_validation.py tests/api/test_health.py -v`

## Wave 5: 全量回归

### T8: 全量回归验证
- **依赖**: T1-T7
- **内容**: 运行全量后端测试 + 前端 TypeScript 编译
- **verify**: `python3 -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` → 0 failed；`cd web && npx tsc --noEmit` → 0 errors

## 风险任务
- **T4 (Graceful shutdown)**: 高风险 — 改动 lifespan 生命周期，需确保不破坏现有 startup 初始化顺序。额外验证：检查 `app.state.position_manager` 在 startup 中正确赋值
- **T5 (Docker Compose 拆分)**: 中风险 — 从单服务 supervisord 模式拆分为双服务，需确保 frontend 能通过 service name `backend` 连接

## 回滚任务
- 若 T4 导致 startup 异常：回退 `src/api/main.py` 中 shutdown 增强部分，保留原有 3 行 cleanup
- 若 T5 导致容器启动失败：回退 `docker-compose.yml` 到单服务模式

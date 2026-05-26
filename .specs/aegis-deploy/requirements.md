# Requirements: aegis-deploy

## 功能需求

### FR-1: 启动时配置验证
- **Given**: 应用启动，`Config` 实例化
- **When**: `model_validator` 在 `apply_profile` 之后执行
- **Then**: 检查 `auth.jwt_secret` 长度 >= 16；检查至少一个 LLM API key 已设置（`llm.api_key` / `llm.providers` 中任一 provider 的 `api_key`）
- **When**: 验证发现问题
- **Then**: 收集到 `_validation_warnings` 列表，不抛出异常（默认非严格模式）
- **When**: `AEGIS_STRICT_VALIDATION=true`
- **Then**: 缺少 critical secrets 时抛出 `ConfigValidationError`，应用启动失败

### FR-2: 优雅关停
- **Given**: 应用收到 SIGTERM 或 SIGINT
- **When**: lifespan shutdown 阶段执行
- **Then**: 1) 停止 scheduler（不再接受新 job）；2) 关闭所有 WebSocket 连接（code=1001）；3) 保存 position_manager 状态；4) 关闭 realtime_manager
- **When**: shutdown 超过 30s
- **Then**: 强制退出，防止 hang

### FR-3: 前端 health check endpoint
- **Given**: 前端 Next.js 服务运行
- **When**: `GET /api/health` 被调用
- **Then**: 返回 JSON `{ status, timestamp, version, uptime, responseTimeMs, backend }`；backend 字段通过探测 `{API_URL}/api/status` 获取；backend 可达时 status="healthy" (200)，不可达时 status="degraded" (503)

### FR-4: Docker Compose 增强
- **Given**: `docker-compose.yml`
- **When**: 部署时
- **Then**: frontend service 有 healthcheck（curl `/api/health`）；backend + frontend 均有 logging 配置（json-file, max-size, max-file）；frontend `depends_on` backend 且 `condition: service_healthy`

### FR-5: Dockerfile 前端 HEALTHCHECK
- **Given**: `Dockerfile` 的 runtime stage
- **When**: 容器运行
- **Then**: 前端 HEALTHCHECK 指令探测 `http://localhost:3000/api/health`

### FR-6: .env.example
- **Given**: 新用户首次配置
- **When**: 复制 `.env.example` 为 `.env`
- **Then**: 包含所有必需和可选环境变量，带分组注释

### FR-7: 测试覆盖
- **Given**: 新增/修改了功能
- **When**: 运行测试套件
- **Then**: 新增 >=4 tests，覆盖配置验证（3 个场景）和 health endpoint（1 个）

## 用户故事
- As a **运维人员**, I want 启动时自动验证关键配置, So that 缺失 secrets 时能立即发现而非运行时崩溃
- As a **运维人员**, I want 优雅关停机制, So that SIGTERM 时 positions 状态不丢失、连接正确关闭
- As a **运维人员**, I want 前端 health check endpoint, So that Docker / K8s 能正确判断前端健康状态
- As a **开发者**, I want `.env.example` 模板, So that 新环境配置时有明确参考

## 非功能需求
### NFR-1: 关停超时保护
shutdown 最多等待 30s，超时后强制退出，防止进程 hang

### NFR-2: 向后兼容
- 不修改现有 router 注册代码
- 不修改 startup 中已有的服务初始化顺序
- `model_validator` 在现有 `apply_profile` 之后执行，不改变其行为

## 边界场景
### Edge-1: 所有 LLM key 都缺失
`_validation_warnings` 包含一条警告；`is_production_ready` 返回 False；严格模式下抛出 `ConfigValidationError`

### Edge-2: JWT secret 为空字符串（默认值）
视为未设置，触发 warning

### Edge-3: shutdown 时 scheduler 已停止
`hasattr` 检查 + try/except 保护，不因重复停止而崩溃

### Edge-4: shutdown 时 WebSocket 连接已断开
遍历 `ws_connections` 时用 try/except 包裹每个 close 调用

### Edge-5: 前端 health check 时 backend 超时
5s 超时后 backend 状态标记为 "unreachable"，整体 status="degraded"

### Edge-6: Dockerfile 中 curl 不可用
Runtime stage 已安装 curl（现有 Dockerfile:48），无需额外处理

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: 后端全量回归 0 failed | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` → 0 failed |
| AC-2: 前端 TypeScript 编译 0 errors | `cd web && npx tsc --noEmit` → 0 errors |
| AC-3: 缺少 JWT secret 时启动有 warning 日志但不 crash | 单元测试：构造 `AegisConfig(auth__jwt_secret="")` 后 `validation_warnings` 非空且不抛异常 |
| AC-4: `AEGIS_STRICT_VALIDATION=true` + 缺少 secret → 启动失败 | 单元测试：`AEGIS_STRICT_VALIDATION=true` + 空 jwt_secret → `ConfigValidationError` |
| AC-5: SIGTERM 后 scheduler 停止 + positions 保存 | 单元测试：mock scheduler/position_manager，验证 `shutdown()` 和 `save()` 被调用 |
| AC-6: `GET /api/health` (frontend) 返回 backend 连通状态 | 单元测试：mock fetch 返回 ok/error，验证 response status 和 body |
| AC-7: docker-compose frontend 有 healthcheck 且 depends_on backend | 代码审查：`docker-compose.yml` 中 frontend service 包含 `healthcheck` 和 `depends_on` |
| AC-8: `.env.example` 包含所有 env vars 及注释 | 代码审查：文件存在且包含 AUTH_JWT_SECRET、LLM_API_KEY、AEGIS_STRICT_VALIDATION 等关键字段 |
| AC-9: 新增 >=4 tests | 统计 `tests/test_config_validation.py` + `tests/api/test_health.py` 中新增 test 函数数量 |

## 回滚计划
- `src/config.py` 的 `model_validator` 可独立移除，不影响其他功能
- `src/api/main.py` 的 shutdown 增强可回退到原有逻辑
- 前端 health check 是独立新文件，删除即可回退
- Docker 配置变更仅影响部署，不影响应用代码

## 数据/权限影响
- 无数据库 schema 变更
- 无新增权限要求
- `.env.example` 不包含任何真实 secret

## 排除范围（Out of Scope）
- `src/agents/`（全部）
- `src/services/`（全部）
- `src/scheduler/engine.py`
- `src/llm/`
- `src/observability/`
- `src/api/routes/positions.py`
- `src/api/routes/settings.py`
- `src/api/routes/tracking.py`
- `src/api/routes/analyze.py`
- `src/api/routes/ws.py`
- `web/app/positions/`
- `web/app/settings/`
- `web/app/analyze/`
- `web/app/tracking/`
- `web/components/`
- `web/hooks/`

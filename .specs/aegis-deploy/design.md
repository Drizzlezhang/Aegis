# Design: aegis-deploy

## 技术方案概述

本 change 在 4 个层面增强部署健壮性：
1. **配置层**：`Config` 新增 `model_validator` 在启动时验证 critical secrets，支持严格模式
2. **应用层**：`lifespan` shutdown 增强为有序关停（scheduler → WS → positions → realtime），带 30s 超时保护
3. **前端层**：新增 `/api/health` endpoint，探测 backend 连通性
4. **基础设施层**：Docker Compose 拆分为 backend/frontend 双服务，增加 healthcheck、logging、depends_on；Dockerfile 增加前端 HEALTHCHECK；新增 `.env.example`

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| ConfigValidator | `src/config.py` | `model_validator` 验证 JWT secret + LLM key；`strict_validation` 控制严格模式 |
| GracefulShutdown | `src/api/main.py` | lifespan shutdown 增强：信号处理、有序关停、超时保护 |
| FrontendHealth | `web/app/api/health/route.ts` | Next.js API route，探测 backend `/api/status`，返回 health JSON |
| DockerConfig | `docker-compose.yml` | 拆分为 backend + frontend 双服务，healthcheck、logging、depends_on |
| DockerfileHealth | `Dockerfile` | 前端 HEALTHCHECK 指令 |
| EnvTemplate | `.env.example` | 环境变量模板 |

## API 设计

### `GET /api/health`（前端 Next.js）

**Response 200** (backend 可达):
```json
{
  "status": "healthy",
  "timestamp": "2026-05-26T00:00:00.000Z",
  "version": "0.1.0",
  "uptime": 12345.6,
  "responseTimeMs": 42,
  "backend": "connected"
}
```

**Response 503** (backend 不可达):
```json
{
  "status": "degraded",
  "timestamp": "2026-05-26T00:00:00.000Z",
  "version": "0.1.0",
  "uptime": 12345.6,
  "responseTimeMs": 5001,
  "backend": "unreachable"
}
```

### `GET /api/status`（后端已有，用于前端 health probe）

已有 endpoint，返回 `{"status": "ok"}`。前端 health check 通过 `fetch` 探测此端点判断 backend 连通性。

## 数据模型

### Config 新增字段

```python
class Config(BaseSettings):
    # ... existing fields ...

    # 新增：严格验证模式
    strict_validation: bool = False  # 环境变量: AEGIS_STRICT_VALIDATION

    # 私有：验证警告收集
    _validation_warnings: list[str] = PrivateAttr(default_factory=list)
```

### ConfigValidationError

```python
class ConfigValidationError(Exception):
    """Raised when strict validation fails."""
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(f"Config validation failed: {len(issues)} issue(s)")
```

### model_validator 执行顺序

```
Config.__init__()
  → field_validators (resolve_paths, validate_symbols)
  → model_validator: apply_profile (已有)
  → model_validator: validate_required_secrets (新增)
```

`validate_required_secrets` 在 `apply_profile` 之后执行，确保 profile 相关的默认值已生效后再检查。

### Lifespan shutdown 流程

```
yield 之后:
  ┌─ logger.info("Shutting down gracefully...")
  ├─ 1. scheduler.shutdown(wait=True)     ← 停止接受新 job
  ├─ 2. WS connections close(code=1001)   ← 通知客户端
  ├─ 3. position_manager.save()           ← 持久化持仓
  ├─ 4. realtime_manager.shutdown()       ← 已有逻辑
  └─ logger.info("Shutdown complete.")
  
  全程包裹在 asyncio.wait_for(..., timeout=30) 中
  超时 → logger.error + 强制退出
```

### Docker Compose 服务拆分

```
Before (单服务):
  aegis-trader:
    image: aegis-trader:latest
    command: supervisord  ← 同时运行 backend + frontend

After (双服务):
  backend:
    image: aegis-trader:latest
    command: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8001
    healthcheck: curl http://127.0.0.1:8001/api/health
    logging: json-file (50m/5)

  frontend:
    image: aegis-trader:latest
    command: cd /app/web && npx next start -p 3000
    healthcheck: curl http://localhost:3000/api/health
    logging: json-file (20m/3)
    depends_on:
      backend:
        condition: service_healthy
```

注意：拆分后不再使用 supervisord，每个服务独立运行一个进程。这符合容器化最佳实践（one process per container）。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `model_validator` 与 pydantic-settings 兼容性 | 启动失败 | 已有 `apply_profile` 使用 `model_validator(mode="after")`，验证模式已确认可用 |
| Docker Compose 拆分后 frontend 无法连接 backend | 前端不可用 | frontend 通过 `depends_on: condition: service_healthy` 确保 backend 就绪后才启动 |
| shutdown 超时 30s 不够 | 数据丢失 | 30s 对于 scheduler.stop() + position.save() 足够；LLM 请求在 scheduler 停止后不再发起新请求 |
| `position_manager` 未存储在 `app.state` 上 | shutdown 无法访问 | 在 startup 中将 `position_manager` 赋值给 `app.state.position_manager` |
| 前端 health check 中 `process.uptime()` 在 Next.js 中不可用 | health endpoint 报错 | 使用 `process.uptime()` 是 Node.js 标准 API，Next.js 支持 |

## 回滚计划
- `src/config.py`：移除 `validate_required_secrets` validator 和 `strict_validation` 字段即可
- `src/api/main.py`：回退 shutdown 逻辑到原有 3 行代码
- `web/app/api/health/route.ts`：删除文件即可
- `docker-compose.yml`：回退到单服务 + supervisord 模式
- `Dockerfile`：移除新增的 HEALTHCHECK 指令
- `.env.example`：删除文件即可

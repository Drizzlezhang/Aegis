# Design: sprint5-master-integration

<!-- size:all -->
## 技术方案概述
按依赖顺序合并三个 Sprint 5 分支（infra → observe → ux），解决冲突后编写跨分支胶水代码，修复 Review P2 问题，最后全量验证提交。集成只做连接与修复，不重写分支内部实现。

## 组件拆分

| 组件 | 来源分支 | 职责 |
|------|---------|------|
| AuthMiddleware | aegis-infra | JWT token 验证，PUBLIC_PATHS 白名单 |
| RateLimitMiddleware | aegis-infra | IP 级别请求限流 |
| auth routes | aegis-infra | /api/auth/login 端点 |
| setup_logging | aegis-observe | 结构化日志初始化 |
| TraceContext | aegis-observe | Pipeline trace_id 传递 |
| metrics routes | aegis-observe | /api/metrics Prometheus 端点 |
| Dashboard UX | aegis-ux | ErrorBoundary, Skeleton, Login, WS UX, responsive |

**集成胶水层**（main.py）组合以上组件：lifespan 内 init logging，middleware stack 注册 rate limit + auth，router 注册 auth + metrics。
<!-- /size:all -->

<!-- size:S+ -->
## API 设计

### Auth 端点（来自 infra）
```
POST /api/auth/login
  Request:  { "api_key": "<secret>" }
  Response: { "token": "<jwt>" }
  Error:    401 { "detail": "Invalid API key" }
```

### Metrics 端点（来自 observe，无需认证）
```
GET /api/metrics
  Response: Prometheus text format
```

### Middleware 栈
```text
Request → RateLimitMiddleware(120 req/min) → AuthMiddleware(JWT verify) → Router
                                                        ↓
                                               PUBLIC_PATHS: /api/health, /api/auth/login, /api/metrics, /docs, /openapi.json → skip auth
```
<!-- /size:S+ -->

<!-- size:M+ -->
## 数据模型

### pyproject.toml 依赖补充
```toml
# 需新增（当前缺失）:
"PyJWT>=2.8.0",        # infra: JWT token 生成/验证
"alembic>=1.13.0",     # infra: 数据库迁移
"asyncpg>=0.29.0",     # infra: PostgreSQL 异步驱动
"aiosqlite>=0.20.0",   # infra: SQLite 异步驱动
```

### Config 新增字段（来自 infra）
```python
class AuthConfig(BaseModel):
    enabled: bool = False
    api_key: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 1440

class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./data/aegis.db"
```

### 前端 token 流
```text
Login → getToken() returns token
     → api.ts getAuthHeaders() adds "Authorization: Bearer <token>"
     → useWebSocket.ts append "?token=<encoded>" to WS URL
     → token 不存在时 → 正常请求，后端 auth.enabled=false 时放行
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| merge conflict 代码丢失 | 编译失败、功能缺失 | merge 前创建 backup 分支；逐文件手工解决冲突 |
| middleware 顺序错误 | 限流失效或认证绕过 | 严格按 RateLimit 外层 → Auth 内层注册；冒烟验证 |
| 依赖缺失致 import 失败 | 编译/运行失败 | py_compile 检查每个关键文件；缺失依赖补入 pyproject.toml |
| 端口不一致 | 前端请求打到错误后端 | next.config.js 改 8001；docker-compose 确认 API_BASE_URL |
| WebSocket token 特殊字符 | URL 解析错误 | encodeURIComponent 处理 token 值 |
| TraceContext 并发覆盖 | 并跑 pipeline 时 trace_id 串扰 | 不修改实现，仅标注 WARNING；Sprint 6 迁移 contextvars |

## 回滚计划
1. `git branch backup/pre-sprint5-integration master` — 在 merge 前创建备份分支
2. 若 merge 中途失败：`git merge --abort` 回到 master 原始状态
3. 若 merge 完成但验证失败：`git reset --hard backup/pre-sprint5-integration`
4. 若已提交但需回滚：`git revert <commit-hash>`
<!-- /size:M+ -->
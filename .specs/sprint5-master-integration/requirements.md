# Requirements: sprint5-master-integration

<!-- size:all -->
## 功能需求

### FR-1: 按依赖顺序合并三分支
- Given: 三个分支 aegis-infra, aegis-observe, aegis-ux 已 push 到 origin 且通过各自验证
- When: 在 master 上执行 `git merge origin/aegis-infra` → `git merge origin/aegis-observe` → `git merge origin/aegis-ux`
- Then: 三分支代码合入 master，冲突文件 (`src/api/main.py`, `src/api/routes/__init__.py`) 按策略解决，无冲突残留

### FR-2: main.py 统一初始化
- Given: 三分支已合入，三方的 middleware/routes/logging 模块已存在
- When: 检查 `src/api/main.py`
- Then: imports 包含 AuthMiddleware, RateLimitMiddleware, setup_logging, auth router, metrics router；lifespan 中调用 setup_logging；middleware 注册顺序 RateLimit 在外层、Auth 在内层；router 注册 auth 和 metrics

### FR-3: 前端 API 请求自动附加 Authorization header
- Given: `web/lib/auth.ts` 提供 `getToken()` 函数
- When: `web/lib/api.ts` 中任意 fetch 调用发起请求
- Then: 若 token 存在，自动附加 `Authorization: Bearer <token>` header；若 token 不存在，正常发请求不报错

### FR-4: WebSocket URL 附加 token
- Given: `web/hooks/useWebSocket.ts` 构建 WebSocket 连接 URL
- When: `getToken()` 返回有效 token
- Then: WS URL 附加以 `?token=<encoded>` 或 `&token=<encoded>` 作为查询参数

### FR-5: PUBLIC_PATHS 包含 /api/metrics
- Given: `src/api/middleware/auth.py` 定义 PUBLIC_PATHS 集合
- When: 请求路径为 `/api/metrics`
- Then: AuthMiddleware 放行该请求，不做认证检查

### FR-6: 端口统一为 8001
- Given: Dockerfile 暴露 8001，docker-compose 使用 8001
- When: `web/next.config.js` 的 rewrites 转发 API 请求
- Then: 默认 `API_BASE_URL` 指向 `http://localhost:8001`

### FR-7: Login 页面 locale 动态化
- Given: 用户浏览器语言设置为英文
- When: 访问 `/login` 页面
- Then: 页面文案显示英文；切换为中文用户时显示中文；不再硬编码 `'zh-CN'`

### FR-8: TraceContext 协程安全警告标注
- Given: `src/observability/logging.py` 中 `TraceContext` 使用类变量存储
- When: 阅读 TraceContext 类定义
- Then: docstring 中包含并发安全 WARNING 和 Sprint 6 TODO 说明

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 三分支成功合入，git log 显示三个 merge commit | `git log --oneline -5` 查看 merge commits |
| AC-2: `src/api/main.py` 无 conflict marker (`<<<<<<<`, `=======`, `>>>>>>>`) | `grep -rE '<<<<<<<|=======|>>>>>>>' src/` 返回空 |
| AC-3: Auth middleware + rate limit + logging 在 main.py 正确注册 | 读取 `src/api/main.py` 内容，确认 imports 和注册代码存在 |
| AC-4: 前端 fetch 请求携带 `Authorization: Bearer <token>` | 读取 `web/lib/api.ts`，确认 `getAuthHeaders()` 函数存在且在 fetch 中调用 |
| AC-5: WebSocket URL 包含 token 查询参数 | 读取 `web/hooks/useWebSocket.ts`，确认 token 拼接逻辑存在 |
| AC-6: `/api/metrics` 在 PUBLIC_PATHS 中 | `grep '/api/metrics' src/api/middleware/auth.py` 有匹配 |
| AC-7: next.config.js 端口为 8001 | `grep 8001 web/next.config.js` 有匹配 |
| AC-8: Login 页面使用动态 locale | `grep "locale" web/app/login/page.tsx` 存在且无 `'zh-CN'` 硬编码 |
| AC-9: TraceContext 有并发安全 warning | `grep -A5 'class TraceContext' src/observability/logging.py` 包含 WARNING |
| AC-10: Python 编译检查全部通过 | `python3 -m py_compile` 对 10 个关键文件无报错 |
| AC-11: TypeScript 类型检查通过 | `cd web && npx tsc --noEmit` 返回 exit code 0 |
| AC-12: 全量测试通过（跳过外部服务相关） | `python -m pytest tests/ -x --tb=short --ignore=...` exit code 0 |
| AC-13: 端到端集成冒烟通过 | 执行冒烟脚本，输出包含 `All Sprint 5 modules integrated successfully` |
| AC-14: Git commit 包含所有变更 | `git log -1 --stat` 显示预期文件列表 |
<!-- /size:all -->

<!-- size:S+ -->
## 用户故事
- As a 开发者, I want 三个分支按依赖顺序合入 master, So that 代码库统一且无冲突
- As a 前端开发者, I want API 请求自动携带认证 token, So that 无需在每个调用点手动添加 header
- As a 运维人员, I want Prometheus 能无认证抓取 /api/metrics, So that 监控系统正常工作
- As a 国际用户, I want Login 页面显示我的语言, So that 登录体验无障碍
<!-- /size:S+ -->

<!-- size:M+ -->
## 非功能需求
### NFR-1: Middleware 顺序
RateLimitMiddleware 必须在外层（先限流），AuthMiddleware 在内层（后认证）。顺序错误会导致限流统计偏差或认证绕过。

### NFR-2: 前端 auth 降级
token 不存在时，请求仍正常发送。后端 `auth.enabled=false` 时放行所有请求，前端不因 token 缺失而阻断请求。

### NFR-3: 不修改分支内部实现
集成只做胶水连接 + Review 修复，不重写、重构或新增功能代码。

### NFR-4: TraceContext 实现不变
当前仅添加注释警告，不改用 contextvars。实际迁移留给 Sprint 6。

## 边界场景
### Edge-1: 分支尚未 push 到 origin
执行 merge 前先 `git fetch origin` 确认远程分支存在。若不存在则终止。

### Edge-2: merge conflict 超出预期文件
若冲突文件不止 `main.py` 和 `routes/__init__.py`，停止自动解决，列出所有冲突文件由用户确认策略。

### Edge-3: 依赖缺失
若 `scipy`, `PyJWT`, `alembic`, `asyncpg`, `aiosqlite` 任一缺失，补入 `pyproject.toml` 的 `dependencies`。

### Edge-4: WebSocket token 编码
token 值可能含特殊字符，必须 `encodeURIComponent` 处理后再拼入 URL。

## 回滚计划
- 合并操作前创建备份分支 `backup/pre-sprint5-integration`
- 若 merge 失败或验证不通过：`git reset --hard backup/pre-sprint5-integration`
- 若已提交但需回滚：`git revert <commit-hash>`

## 数据/权限影响
- 无数据库 schema 变更
- PUBLIC_PATHS 新增 `/api/metrics`，降低该路径的访问控制
<!-- /size:M+ -->
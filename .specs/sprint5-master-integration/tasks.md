# Tasks: sprint5-master-integration

<!-- size:all -->
## 任务波次

### Wave 1: Merge（按依赖顺序，不可并行）
#### T01: 创建备份分支
- 描述: merge 前创建 backup 分支以支持回滚
- read_files: none
- write_files: none (git operation)
- verify: `git branch | grep backup/pre-sprint5-integration`
- status: pending

#### T02: Merge aegis-infra
- 描述: 合入 infra 分支（auth, rate limit, DB, Docker, CI），解决 main.py 和 routes/__init__.py 冲突
- depends_on: [T01]
- read_files: [`src/api/main.py`, `src/api/routes/__init__.py`]
- write_files: [`src/api/main.py`, `src/api/routes/__init__.py`]
- verify: `git log --oneline -1 | grep "merge.*infra"` 且 `grep -rE '<<<<<<<|=======|>>>>>>>' src/` 返回空
- status: pending

#### T03: Merge aegis-observe
- 描述: 合入 observe 分支（logging, tracing, metrics, GEX BSM, checkpoint），解决冲突
- depends_on: [T02]
- read_files: [`src/api/main.py`, `src/api/routes/__init__.py`]
- write_files: [`src/api/main.py`, `src/api/routes/__init__.py`]
- verify: `git log --oneline -1 | grep "merge.*observe"` 且冲突残留检查通过
- status: pending

#### T04: Merge aegis-ux
- 描述: 合入 ux 分支（ErrorBoundary, Skeleton, Login, WS UX, responsive），纯前端无后端冲突
- depends_on: [T03]
- read_files: none
- write_files: none (git merge only)
- verify: `git log --oneline -1 | grep "merge.*ux"` 且 `grep -rE '<<<<<<<|=======|>>>>>>>' web/` 返回空
- status: pending
<!-- /size:all -->

<!-- size:S+ -->
### Wave 2: Glue Code（依赖 Wave 1 全部完成）
#### T05: main.py 胶水 — logging 初始化 + middleware + routes
- 描述: lifespan 中添加 setup_logging 调用；确认 AuthMiddleware + RateLimitMiddleware 注册顺序（RateLimit 外层）；确认 auth + metrics router 注册
- depends_on: [T02, T03]
- read_files: [`src/api/main.py`, `src/api/middleware/auth.py`, `src/api/middleware/rate_limit.py`, `src/observability/logging.py`]
- write_files: [`src/api/main.py`]
- verify: `python3 -m py_compile src/api/main.py` 且 grep 确认 imports 和注册代码存在
- status: pending

#### T06: PUBLIC_PATHS 补充 /api/metrics
- 描述: 在 auth.py 的 PUBLIC_PATHS 集合中添加 `/api/metrics`
- depends_on: [T02]
- read_files: [`src/api/middleware/auth.py`]
- write_files: [`src/api/middleware/auth.py`]
- verify: `grep '/api/metrics' src/api/middleware/auth.py` 有匹配
- status: pending

#### T07: 前端 API 自动附加 Authorization header
- 描述: 在 api.ts 中导入 getToken，创建 getAuthHeaders()，在所有 fetch 调用中合并 headers
- depends_on: [T04]
- read_files: [`web/lib/api.ts`, `web/lib/auth.ts`]
- write_files: [`web/lib/api.ts`]
- verify: `grep 'Authorization' web/lib/api.ts` 有匹配
- status: pending

#### T08: WebSocket URL 附加 token
- 描述: 在 useWebSocket.ts 中导入 getToken，connect 函数内拼接 token 查询参数
- depends_on: [T04]
- read_files: [`web/hooks/useWebSocket.ts`, `web/lib/auth.ts`]
- write_files: [`web/hooks/useWebSocket.ts`]
- verify: `grep 'getToken' web/hooks/useWebSocket.ts` 有匹配
- status: pending
<!-- /size:S+ -->

### Wave 3: Review Fixes（依赖 Wave 2 glues）
#### T09: 端口统一 — next.config.js 8003 → 8001
- 描述: rewrites 中 `localhost:8003` 改为 `localhost:8001`；同时使用环境变量 API_BASE_URL 作为 fallback
- depends_on: []  (可独立执行)
- read_files: [`web/next.config.js`]
- write_files: [`web/next.config.js`]
- verify: `grep 8001 web/next.config.js` 有匹配，`grep 8003 web/next.config.js` 无匹配
- status: pending

#### T10: Login 页面 locale 动态化
- 描述: 将硬编码 `getMessage('zh-CN', ...)` 全部替换为 `getMessage(locale, ...)`，`locale` 从 `useLocale()` 获取
- depends_on: [T04]
- read_files: [`web/app/login/page.tsx`, `web/components/LocaleProvider.tsx`]
- write_files: [`web/app/login/page.tsx`]
- verify: `grep "locale" web/app/login/page.tsx` 存在，`grep "'zh-CN'" web/app/login/page.tsx` 无匹配
- status: pending

#### T11: TraceContext 协程安全警告标注
- 描述: TraceContext 类 docstring 添加 WARNING 和 Sprint 6 TODO
- depends_on: [T03]
- read_files: [`src/observability/logging.py`]
- write_files: [`src/observability/logging.py`]
- verify: `grep -A5 'class TraceContext' src/observability/logging.py | grep WARNING` 有匹配
- status: pending

### Wave 4: Verify & Ship（依赖前 3 波全部完成）
#### T12: 依赖确认 + 编译/类型检查 + 全量测试 + 冒烟 + 提交
- 描述: 确认缺失依赖补入 pyproject.toml（PyJWT, alembic, asyncpg, aiosqlite）；Python 编译检查；TS 类型检查；全量测试；端到端冒烟；git commit
- depends_on: [T05, T06, T07, T08, T09, T10, T11]
- read_files: [`pyproject.toml`]
- write_files: [`pyproject.toml`] (可能)
- verify: 14 条 AC 全部通过
- status: pending
<!-- /size:S+ -->

<!-- size:M+ -->
## 风险任务
| 任务 | 风险 | 前置条件 | 额外验证 |
|------|------|---------|---------|
| T02-T04 merge | 冲突代码丢失 | backup 分支已创建 | 逐文件 review diff；py_compile 关键文件 |
| T05 main.py 胶水 | import 失败、middleware 顺序错 | infra + observe 已合入 | 冒烟脚本全覆盖 |
| T12 依赖补充 | 版本冲突致 pip install 失败 | pyproject.toml 已更新 | `pip install -e .` 试装 |

## 回滚任务
- 若 T02-T04 任一步 merge 失败：`git merge --abort`，检查冲突文件
- 若 T12 验证失败：`git reset --hard backup/pre-sprint5-integration`
- 若已提交但需回滚：`git revert <commit-hash>`
<!-- /size:M+ -->
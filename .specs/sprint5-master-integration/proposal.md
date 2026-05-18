# Change: sprint5-master-integration

## 概述
Sprint 5 三分支（aegis-infra, aegis-observe, aegis-ux）合入 master，完成胶水代码连接与 Review P2 修复。

## 动机
三个分支已完成 Sprint 5 独立开发并通过各自验证和 Review。需要按依赖顺序合入 master，解决合并冲突，编写跨分支胶水代码，修复 Review 发现的 P2 问题，完成全量验证与提交。

## 影响范围
- `src/api/main.py` — merge conflict resolve + logging 初始化
- `src/api/routes/__init__.py` — merge conflict resolve
- `src/api/middleware/auth.py` — PUBLIC_PATHS 补充 metrics
- `src/observability/logging.py` — TraceContext 协程安全警告标注
- `web/lib/api.ts` — fetch 自动附加 Authorization header
- `web/hooks/useWebSocket.ts` — WebSocket URL 附加 token
- `web/next.config.js` — 端口 8003 → 8001
- `web/app/login/page.tsx` — locale 动态化
- `pyproject.toml` — 依赖确认（可能补充）

## 验收目标
1. 三分支成功合入 master，无冲突残留
2. Auth middleware + rate limit + logging 在 main.py 正确初始化
3. 前端请求自动携带 token，WebSocket 附加认证参数
4. /api/metrics 无需认证即可访问
5. 全栈端口统一为 8001
6. Login 页面根据用户 locale 动态切换语言
7. TraceContext 添加并发安全警告注释
8. Python 编译检查 + TypeScript 类型检查通过
9. 全量测试通过（跳过需外部服务的测试）
10. 端到端集成冒烟通过

## Size: M
## 推断依据
- 范围：跨模块（api/middleware/observability/web），涉及 8+ 文件
- 关键词：merge, integrate, wire, fix — 集成+修复，非新功能开发
- 预估文件数：8-10
- 依赖变更：仅内部模块间胶水连接
- 风险：需回归测试，merge conflict 有破坏风险
- project.yaml scale=L 但任务本质是集成，综合判断为 M

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
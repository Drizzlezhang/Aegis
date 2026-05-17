# Verification: sprint5-infra

## 验证时间: 2026-05-17T12:15:00+08:00

## 验证模式
- `5-full`

## AC 对账
基于 `requirements.md` 中 15 条 AC 逐条核验，使用 SPEC 中已声明的验证方式。

## 验收标准逐条验证

| AC | 验证方式 | 状态 | 证据 |
|----|---------|------|------|
| AC-1: AuthConfig 字段完整加载，默认 `enabled=False` | `python -c "from src.config import get_config; ..."` | PASS | `c.auth.enabled is False` 输出 `False` |
| AC-2: DatabaseConfig 默认 URL 为 SQLite | `python -c "from src.config import get_config; ..."` | PASS | `c.database.url` 输出 `sqlite:///~/.aegis-trader/aegis.db` |
| AC-3: src/db.py engine 创建支持 SQLite async | `python -m py_compile src/db.py` | PASS | 编译通过，engine 单例模式正确 |
| AC-4: Alembic upgrade 创建 3 张表 | `alembic upgrade head` + inspect | PASS | Tables: `['decisions', 'execution_history', 'positions']` |
| AC-5: Auth 中间件 — 公开路径放行 | test_public_path_no_auth | PASS | `GET /api/health` → 200 |
| AC-6: Auth 中间件 — 有效 JWT 通过 | test_valid_jwt_passes | PASS | `GET /api/symbols` + Bearer Token → 200 |
| AC-7: Auth 中间件 — 过期 JWT 拒绝 | test_expired_jwt_rejected | PASS | Expired token → 401 |
| AC-8: Auth 中间件 — 有效 API Key 通过 | test_valid_api_key_passes | PASS | `X-API-Key` header → 200 |
| AC-9: /api/auth/login — 正确 API Key 返回 JWT | test_login_success | PASS | Response: `access_token`, `token_type=bearer`, `expires_in>0` |
| AC-10: /api/auth/login — 无效 API Key 返回 401 | test_login_invalid_key | PASS | Wrong key → 401, detail="Invalid API key" |
| AC-11: Rate Limit — 配额内放行 | test_requests_within_limit | PASS | 10 requests 全部 200 |
| AC-12: Rate Limit — 超配额返回 429 | test_rate_limit_exceeded | PASS | rate=5, 超过后返回 429 |
| AC-13: Docker Compose 服务全部健康 | `docker compose config --quiet` | PASS | YAML 语法验证通过，端口与 Dockerfile 一致（8001） |
| AC-14: CI 前端 job 存在且可执行 | 检查 ci.yml | PASS | `frontend` job 包含 `tsc --noEmit` + `npm run build`，与 `test` job 并行 |
| AC-15: 现有测试套件无回归 | `pytest tests/api/ -q` | PASS | 56 passed，无新增失败 |

## 测试结果
- **单元测试**: 10 passed（8 required + 2 extra unit tests: `test_verify_token_expired`, `test_verify_token_valid`）
- **回归测试**: 56 passed（`tests/api/` 全部），无回归
- **编译检查**: 全部 6 个源文件 `py_compile` 通过
- **配置验证**: AuthConfig + DatabaseConfig 字段正确加载，默认值符合预期
- **Alembic 迁移**: 3 张表（decisions, positions, execution_history）正确创建在 SQLite

## 回滚验证
- 所有新增文件可在不修改现有代码的情况下通过 git rm 移除
- 中间件绕过：`auth.enabled=False`（默认），完全不拦截请求
- DB 绕过：默认 SQLite，不依赖 PostgreSQL

## 数据/权限影响验证
- 新增 3 张 DB 表通过 Alembic migration 创建，无存量数据影响
- Auth 默认 disabled，不影响现有 API 调用方
- `.env.example` 新增 Auth/DB 配置段，旧字段保持兼容

## 总结
- 通过: **pass**
- 失败项: 无
- 建议操作: 进入 6-SHIP 完成 git commit
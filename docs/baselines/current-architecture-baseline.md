# Current Architecture Baseline

## Context
本文件用于固化结构重构前的当前工程基线，确保后续目录迁移、边界收敛和 `CLAUDE.md` 规则落地都有明确参照。该基线只描述当前真实状态，不引入新的业务语义，也不修改任何业务逻辑或 UI 交互。

## Repository Reality
当前仓库是同一 Git 仓库下的前后端并存结构，而不是标准 workspace monorepo：

- `web/`：Next.js 前端应用
- `src/`：Python 主业务源码
- `tests/`：Python 测试目录
- `deploy/`：部署脚本与进程配置
- `CLAUDE.md`：仓库级开发约束
- `pyproject.toml`：Python 项目入口与依赖

## Frontend Baseline
### Entry points
- `web/package.json`
  - `dev`: `next dev`
  - `build`: `next build`
  - `start`: `next start`
  - `test`: `vitest run`
- `web/app/layout.tsx`
  - 前端全局布局入口，挂载 `AppThemeProvider` 与 `LocaleProvider`
- `web/app/page.tsx`
  - 首页入口，依赖 `Header`、`Sidebar`、`SymbolCard`、`MarketIndexCard`、`MarketSentimentInline`

### Main route slices
- `web/app/page.tsx`
- `web/app/analyze/page.tsx`
- `web/app/market/page.tsx`
- `web/app/status/page.tsx`
- `web/app/memory/page.tsx`
- `web/app/backtest/page.tsx`
- `web/app/history/page.tsx`
- `web/app/history/[id]/page.tsx`
- `web/app/symbol/[symbol]/page.tsx`

### Shared frontend foundations already present
- `web/components/*`
  - 当前主要共享 UI 聚合目录
- `web/components/theme/AppThemeProvider.tsx`
  - 当前主题 provider 入口
- `web/components/LocaleProvider.tsx`
  - 当前 locale provider 入口
- `web/i18n/*`
  - 当前 i18n 消息与读取逻辑
- `web/lib/api.ts`
  - 当前前端统一 API 调用入口
- `web/lib/theme/theme-storage.ts`
  - 当前主题持久化逻辑

### Frontend runtime assumptions
- 前端默认通过 Next.js App Router 提供页面与 BFF route
- 前端在开发和生产下均依赖后端 API 可达
- 主题与语言通过 provider 注入，不应在结构重构中改变用户可见行为

## Backend Baseline
### Entry points
- `pyproject.toml`
  - Python 包名：`aegis-trader`
  - Python 要求：`>=3.12`
  - CLI script：`aegis-trader = "src.cli:main"`
- `src/cli.py`
  - 当前命令行入口，承载 `analyze` / `list-skills` / `health` / `status` / `reload-config` / `api` 等命令
- `src/api/main.py`
  - 当前 FastAPI 入口，挂载 `/api/health` 和各业务路由

### Main backend slices
- `src/api/routes/*`
  - API route 层
- `src/agents/*`
  - Agent 实现与 orchestrator
- `src/skills/base.py`
  - Skill 抽象基类
- `src/skills/registry.py`
  - Skill 注册中心
- `src/llm/*`
  - 模型路由与客户端

### Backend runtime assumptions
- CLI 与 API 启动均依赖 `src` 包从仓库根正确解析
- API 通过 FastAPI 生命周期初始化 orchestrator
- `src/skills/registry.py` 是当前最成熟的可复用注册/发现模式
- 结构重构时不得改变既有 API contract 与业务输出语义

## Tests Baseline
### Verified in isolated worktree
Worktree:
- `/Users/bytedance/Develop/trade/TradeAgent/.worktrees/refactor-structure`
- Branch: `refactor/structure-boundaries`

### Python
Command:
```bash
python3 -m pytest tests --tb=short
```
Observed result:
- `350 passed`

### Web
Command:
```bash
npm --prefix web test
```
Observed result:
- `14 files / 29 tests passed`

## Deployment Baseline
### Config / script defaults
- `deploy/ecosystem.config.js`
  - PM2 下定义了 `aegis-trader-analyzer` 与 `aegis-trader-web` 两个进程项
  - `aegis-trader-analyzer`：通过 `python -m src.cli analyze --all` 启动，`cwd` 为 `/app`
  - `aegis-trader-web`：通过 `npm start` 启动，`cwd` 为 `/app/web`
  - web 环境变量把 `PORT=3000` 与 `NEXT_PUBLIC_API_URL=http://localhost:8000` 作为 PM2 默认值写入配置
- `deploy/supervisord.conf`
  - `backend`：通过 `uvicorn src.api.main:app --port 8001` 启动，`directory` 为 `/app`
  - `frontend`：通过 `npm start` 启动，`directory` 为 `/app/web`
- `deploy/deploy.sh`
  - 目标路径：`/opt/aegis-trader`
  - 默认分支：`master`
  - 默认通过 `docker compose build --no-cache` 和 `docker compose up -d` 部署
  - 部署脚本依赖当前仓库顶层结构和固定路径假设

### Human-readable deployment docs
- `deploy/README.md`
  - 以 `systemd + supervisord` 描述生产环境进程管理
  - 健康检查示例指向 `http://localhost:8001/api/health`

### Baseline interpretation
- 当前仓库里同时存在 PM2、supervisord、systemd 与 docker compose 相关表述。
- 仅基于静态文件，可先区分哪些属于配置 / 脚本默认值，哪些属于面向人阅读的说明；但不能把这些表述直接合并成单一部署真相。
- `8000` 与 `8001` 的端口差异、以及多套进程管理角色之间的关系，当前仍属于待确认项。

## Constraints For Refactor
- 不修改任何业务逻辑
- 不修改任何 UI 交互或视觉语义
- 不改变既有 API contract
- 不在未完成基线替代方案前贸然移动部署入口和启动脚本

## Implications For Next Phases
1. 后续结构重构必须先兼容 `web/`、`src/`、`tests/`、`deploy/` 的现有入口。
2. 前端优先做 feature/shared/foundation 逻辑收敛，再决定是否物理迁移。
3. 后端优先保留 `src/api/main.py`、`src/cli.py`、`src/skills/registry.py` 等稳定入口与模式。
4. 目录级 `CLAUDE.md` 应在各目录职责稳定后同步补齐，不能先于结构强行落规则。

# 结构一致性审计（Phase 3 最小前置）

## 1. 审计定位
本文用于承接 Phase 2 规则落位之后的最小一致性审计，目标是检查当前仓库真实结构、职责分布与依赖方向，是否与以下规则源保持一致：

- `CLAUDE.md`
- `web/CLAUDE.md`
- `src/CLAUDE.md`
- `docs/baselines/current-architecture-baseline.md`
- `docs/baselines/frontend-logic-boundary-rules.md`
- `docs/baselines/backend-logic-boundary-rules.md`
- `docs/baselines/claude-md-placement-strategy.md`

本文只记录“规则-现状差异”与后续候选治理切片，不直接承诺目录迁移，也不在本轮修改业务逻辑、UI 交互、API contract、模型路由、部署或测试链路。

## 2. 审计范围
### 2.1 前端
- `web/app/*`
- `web/components/*`
- `web/lib/*`
- `web/i18n/*`

### 2.2 后端
- `src/api/*`
- `src/agents/*`
- `src/skills/*`
- `src/llm/*`
- `src/cli.py`
- `src/config.py`

### 2.3 跨目录与仓库级
- 根 `CLAUDE.md` 与局部 `CLAUDE.md` 的分层关系
- `web/` 与 `src/` 的职责边界
- `deploy/`、`pyproject.toml` 对现有目录结构的路径假设

## 3. 审计维度
1. 目录职责是否与已落位规则一致。
2. 是否存在反向依赖、越层引用或职责漂移。
3. 现状基线中的稳定入口，是否仍被当作稳定入口使用。
4. 是否存在适合后续拆分治理、但当前不宜直接迁移的结构债务。

## 4. 现状证据与结论
### 4.1 仓库级分层入口
- 证据：根 `CLAUDE.md` 已明确 root / `web/` 的第一层分层关系，并限定当前阶段不继续下钻二级 `CLAUDE.md`。`src/CLAUDE.md` 也已补齐，形成 root + web + src 三层入口。
  - `CLAUDE.md:42`
  - `web/CLAUDE.md:2`
  - `src/CLAUDE.md:2`
- 结论：**符合**
- 说明：Phase 2 的最小规则落位目标已经完成，当前没有继续新增二级 `CLAUDE.md` 的必要。

### 4.2 前端入口与 API 边界
- 证据：以首页 route file 为抽样样本，`web/app/page.tsx` 主要负责页面装配与数据组织，消费 `@/lib/api` 与展示组件，没有直接拼接后端协议细节。
  - `web/app/page.tsx:1`
  - `web/app/page.tsx:7`
- 证据：`web/lib/api.ts` 作为统一前端 API 入口，集中定义请求构造、共享 fetch 行为和前端类型。
  - `web/lib/api.ts:137`
  - `web/lib/api.ts:152`
- 结论：**符合**
- 说明：基于首页 route file 抽样结果，当前方向与 `web/CLAUDE.md`、`frontend-logic-boundary-rules.md` 中“route file 负责 orchestration、API 边界不反向依赖页面文件”的规则一致。

### 4.3 前端共享层与路由层反向依赖风险
- 证据：分别针对 `web/components/**/*.{ts,tsx,js,jsx}`、`web/lib/**/*.{ts,tsx,js,jsx}`、`web/i18n/**/*.{ts,tsx,js,jsx}` 做了两轮静态扫描，未发现指向 `web/app/*` 的明显 import 命中；补充的 `app/` 片段搜索也未见直接命中。
- 证据：`web/CLAUDE.md` 与 `frontend-logic-boundary-rules.md` 已明确约束 shared UI / lib / i18n 不应反向依赖 route files。
  - `web/CLAUDE.md:22`
  - `web/CLAUDE.md:26`
  - `web/CLAUDE.md:30`
  - `web/CLAUDE.md:46`
  - `docs/baselines/frontend-logic-boundary-rules.md:119`
- 结论：**基本符合**
- 说明：基于当前对明显 import 模式与 `app/` 片段引用的补充扫描，尚未发现 `web/components`、`web/lib`、`web/i18n` 对 `web/app/*` 的直接反向依赖证据；但这仍不替代对动态导入、别名重导出或更完整依赖图的系统核查，因此不应上升为“完全无反向依赖”的强结论。

### 4.4 后端 API 入口与编排层关系
- 证据：`src/api/main.py` 通过 `Orchestrator` 初始化编排能力，并挂载各 route；入口层未见直接接入供应商模型客户端。
  - `src/api/main.py:7`
  - `src/api/main.py:17`
  - `src/api/main.py:45`
- 结论：**符合**
- 说明：与 `backend-logic-boundary-rules.md` 中“入口分离 + 编排集中”的主干模式一致。

### 4.5 后端入口层直连模型客户端风险
- 证据：对 `src/api/*` 做明显 import 模式的初步扫描，未发现入口层直接 import `src.llm`、`src.skills` framework 中心逻辑或明显直连模型客户端的命中。
- 证据：`src/api/main.py` 仅引入 `Orchestrator` 与 route 模块，入口职责主要是应用初始化、路由挂载与生命周期装配。
  - `src/api/main.py:7`
  - `src/api/main.py:9`
  - `src/api/main.py:29`
- 结论：**符合**
- 说明：就当前入口聚合层与 route 层的抽样证据看，未见明显越层依赖；但这仍不替代对所有 route 文件的全量依赖图核查。

### 4.6 后端 CLI 入口层依赖边界
- 证据：`src/cli.py` 直接引入了 `Orchestrator`、`get_global_registry` 与 `get_llm_client`。
  - `src/cli.py:8`
  - `src/cli.py:10`
  - `src/cli.py:11`
- 证据：`check_health()` 直接初始化 LLM 客户端，`list_skills()` 直接驱动 registry 做技能发现，`run_analysis()` 直接创建 `Orchestrator` 并调用分析流程。
  - `src/cli.py:77`
  - `src/cli.py:121`
  - `src/cli.py:33`
  - `src/cli.py:40`
  - `src/cli.py:45`
- 结论：**偏离但暂不修复**
- 说明：按入口层边界规则，CLI 入口更理想的职责应是参数解析、模式选择与结果输出编排；当前 `cli.py` 直接触达 orchestrator、registry 与 LLM client，属于入口层与下层能力边界耦合偏重的现状。该问题已足以作为后续独立治理切片，但本轮不直接改代码。

### 4.7 `src/skills/` 与顶层 `skills/` 双轨语义
- 证据：规则层已明确：`src/skills/*` 是 Skill Framework Layer，顶层 `skills/*` 是 Skill Implementation Layer。
  - `docs/baselines/backend-logic-boundary-rules.md:135`
  - `docs/baselines/backend-logic-boundary-rules.md:140`
  - `docs/baselines/backend-logic-boundary-rules.md:218`
  - `src/CLAUDE.md:26`
  - `src/CLAUDE.md:54`
- 证据：当前 `src/skills/` 实际文件集中在 `base.py`、`registry.py` 与导出入口，职责覆盖接口契约、发现/注册/加载与全局 registry 获取，没有落地具体业务 Skill 实现。
  - `src/skills/base.py:37`
  - `src/skills/registry.py:48`
  - `src/skills/registry.py:62`
  - `src/skills/registry.py:177`
- 证据：当前顶层 `skills/*` 实际文件集中在 `skill.py` / `skill.yaml` 及局部实现支撑文件；具体 Skill 实现通过继承 `src.skills.base.BaseSkill` 落地，没有在顶层目录中发现 registry / discovery 中心逻辑。
  - `skills/data_sources/yfinance_skill/skill.py:13`
  - `skills/data_sources/yfinance_skill/skill.py:18`
  - `skills/algorithms/gex_calculator/skill.py:12`
  - `skills/algorithms/gex_calculator/skill.py:23`
- 证据：当前仓库对两条路径的消费方式呈现双轨并存：一部分调用方通过 `src.skills` 消费 framework 能力，另一部分调用方直接 import 顶层 `skills/*` 的具体实现类。
  - `src/agents/data_harvester/agent.py:9`
  - `src/api/routes/market.py:7`
  - `src/api/routes/symbols.py:10`
  - `src/api/routes/symbols.py:12`
  - `src/backtest/engine.py:8`
  - `src/backtest/engine.py:156`
- 结论：**基本符合**
- 说明：基于当前对目录内容、明显 import 模式与关键样本的抽样回读，`src/skills/*` 与顶层 `skills/*` 的 framework / implementation 双轨语义已被仓库真实结构与主要引用方式支撑；当前更突出的问题不是“语义未定义”，而是双轨命名与直接 import implementation 的消费方式仍提高理解成本。因此，本项可从“规则已澄清但未核查”推进为“结构上基本符合、认知成本仍偏高”，但还不能据此推出“后续已无需继续治理”的强结论。

### 4.8 部署与仓库路径假设
- 证据：`pyproject.toml` 继续把 Python 包稳定入口固定为 `src.cli:main`，说明当前打包与命令行分发仍依赖 `src` 作为仓库根下的稳定解析入口。
  - `pyproject.toml:63`
  - `pyproject.toml:64`
  - `pyproject.toml:67`
- 证据：`deploy/ecosystem.config.js` 继续把 analyzer 工作目录固定为 `/app`，通过 `python -m src.cli analyze --all` 启动；同时把 web 工作目录固定为 `/app/web`，并在 PM2 环境变量里写死 `PORT=3000` 与 `NEXT_PUBLIC_API_URL=http://localhost:8000`。
  - `deploy/ecosystem.config.js:3`
  - `deploy/ecosystem.config.js:5`
  - `deploy/ecosystem.config.js:6`
  - `deploy/ecosystem.config.js:29`
  - `deploy/ecosystem.config.js:32`
  - `deploy/ecosystem.config.js:39`
  - `deploy/ecosystem.config.js:40`
- 证据：`deploy/supervisord.conf` 继续把 backend 工作目录固定为 `/app`，通过 `uvicorn src.api.main:app --port 8001` 启动；frontend 工作目录固定为 `/app/web`，说明 supervisord 方案同样依赖当前顶层结构与入口路径。
  - `deploy/supervisord.conf:7`
  - `deploy/supervisord.conf:8`
  - `deploy/supervisord.conf:10`
  - `deploy/supervisord.conf:18`
  - `deploy/supervisord.conf:20`
- 证据：`deploy/deploy.sh` 继续把部署脚本默认目标目录写为 `/opt/aegis-trader`，默认分支写为 `master`，并通过 `docker compose build --no-cache` / `docker compose up -d` 完成部署。
  - `deploy/deploy.sh:9`
  - `deploy/deploy.sh:10`
  - `deploy/deploy.sh:13`
  - `deploy/deploy.sh:121`
  - `deploy/deploy.sh:124`
- 证据：`deploy/README.md` 继续把部署说明表述为 `systemd + supervisord`，健康检查示例指向 `http://localhost:8001/api/health`，并以 `git pull origin master` 表述默认拉取策略。
  - `deploy/README.md:9`
  - `deploy/README.md:60`
  - `deploy/README.md:158`
- 结论：**基本符合，但存在待确认项**
- 说明：基于当前对 `deploy/**`、`pyproject.toml` 与 baseline 文档的静态回读，可以确认部署相关脚本、配置与文档已经把固定目录、固定入口、固定分支等约束编码为默认假设，因此这部分已不再只是抽象约束，而是后续结构迁移必须显式兼容的静态前提。同时，PM2 环境变量中的 `NEXT_PUBLIC_API_URL=http://localhost:8000` 若其意图是直连后端，则与 `supervisord.conf` / `deploy/README.md` 中的 `8001` 端口表述存在差异；此外，当前仓库内可以确认的是 PM2、supervisord、docker compose、systemd 等部署脚本与文档表述并存，而不是仅凭本地静态文件就断言生产环境实际并存多套进程模型。因此更稳妥的结论应是“部署路径假设已在配置与脚本层被明确编码，但端口约定与部署表述仍有待后续收敛”，而不是把现状误写成单一、完全一致的部署真相。

## 5. 审计摘要
### 5.1 已符合
- root / `web/` / `src/` 三层规则入口已落位。
- 前端首页 route file 抽样与 API 边界方向基本符合局部规则。
- 后端 API 聚合入口与编排层分离方向基本符合局部规则。
- `src/skills/` 与顶层 `skills/` 的 framework / implementation 双轨语义，已被当前目录内容与主要引用方式基本支撑。

### 5.2 待确认
- 前端共享层是否存在更隐蔽的 route 反向依赖。
- 部署链路中的端口约定与进程管理表述仍存在并存情况，尚不能仅凭本地静态文件收敛为单一运行真相。

### 5.3 偏离但暂不迁移
- `src/cli.py` 直接触达 orchestrator、registry 与 LLM client，入口层耦合偏重，适合作为后续独立治理切片。
- `src/skills/` 与顶层 `skills/` 的双轨命名语义虽已被现状支撑，但直接 import implementation 的消费方式仍增加理解成本；当前先不进入物理收敛。
- `deploy/` 与 `pyproject.toml` 已把当前顶层结构、稳定入口与默认分支编码为配置与脚本层默认假设；后续若进入物理迁移，必须单独处理部署、打包与运行时配置影响。

## 6. 后续候选治理切片
> 说明：以下候选切片延续自本文前序审计结果；其中“后端 CLI 入口收敛子任务”“前端 import 图审计子任务”“Skill 双轨语义核查子任务”“跨目录依赖 DAG 审计子任务”“部署路径假设核查子任务”已分别被前序轮次推进或在本轮完成最小核查，因此这里保留当前更适合继续推进的后续候选。

1. **Skill 双轨消费方式收敛子任务（候选）**
   - 目标：在不做物理迁移的前提下，进一步确认哪些调用路径应继续通过 framework registry 获取能力，哪些路径允许直接消费顶层 implementation，以降低双轨理解成本。
2. **部署端口与进程模型表述收敛子任务（候选）**
   - 目标：在不改真实部署方案的前提下，收敛 `deploy/**` 与部署文档中关于 backend 端口、web API 指向与 PM2 / supervisord / systemd / docker compose 角色分工的表述差异，降低后续结构治理时的运行假设歧义。

## 7. 本轮结论
本轮补充审计收敛的是部署路径假设这一子范围。基于当前对 `deploy/**`、`pyproject.toml` 与 `current-architecture-baseline.md` 的静态搜索及关键样本回读，可以确认当前仓库已经在配置、脚本与文档层把 `/app`、`/app/web`、`/opt/aegis-trader`、`src.cli:main`、`python -m src.cli analyze --all`、`uvicorn src.api.main:app`、`master` 等路径与入口编码为默认假设，因此“部署路径假设仍构成后续迁移约束”可以从抽象判断推进为有证据支撑的审计结论。与此同时，PM2 环境变量里的 `8000` 与 supervisord / README 中的 `8001` 端口表述仍可能存在差异，且当前能确认的是多套部署脚本与文档表述并存，而非生产环境实际并存多套进程模型，所以本轮更准确的结论是：部署路径假设已在静态配置层被明确固化并成为结构迁移前提，但端口约定与部署表述仍有待后续独立治理；本轮不直接进入部署整改或目录迁移。


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
- 证据：当前仓库对两条路径的消费方式仍呈双轨并存，但已出现最小运行时收敛：一部分调用方通过 `src.skills` 消费 framework 能力；此前存在于 `src/api/routes/symbols.py`、`src/backtest/engine.py` 的运行时 direct implementation import，本轮已分别收敛为通过 registry 获取 skill 实例；与此同时，测试层 direct implementation import 仍然存在，但基于本轮对 `tests/test_volume_profile.py`、`tests/test_gex.py`、`tests/test_yfinance_skill.py`、`tests/test_futu_skill.py` 与 `tests/skills/test_futu_skill.py` 的补充回读，这些样本目前主要仍属于 implementation-level unit test，而不是已确认需要继续向 framework / registry seam 收敛的运行时消费路径。
  - `src/agents/data_harvester/agent.py:9`
  - `src/api/routes/market.py:7`
  - `src/api/routes/symbols.py:10`
  - `src/api/routes/symbols.py:19`
  - `src/backtest/engine.py:8`
  - `src/backtest/engine.py:18`
  - `tests/test_volume_profile.py:10`
  - `tests/test_gex.py:10`
  - `tests/test_yfinance_skill.py:13`
  - `tests/test_futu_skill.py:8`
  - `tests/skills/test_futu_skill.py:8`
- 结论：**基本符合，但运行时收敛仅完成最小样本，测试层边界以保留为主**
- 说明：基于当前对目录内容、明显 import 模式与关键样本的抽样回读，`src/skills/*` 与顶层 `skills/*` 的 framework / implementation 双轨语义已被仓库真实结构与主要引用方式支撑；当前更突出的问题已不只是“双轨命名增加理解成本”，而是 tests-only 便利性与运行时依赖边界仍需继续区分。本轮已先把 `src/api/routes/symbols.py` 与 `src/backtest/engine.py` 两个已确认运行时样本收敛为 framework / registry 消费路径，说明这类收敛在当前代码结构中可行；但补充回读后的测试样本显示，当前剩余 direct implementation import 主要集中在 implementation-level unit test：例如 `tests/test_volume_profile.py`、`tests/test_gex.py` 直接验证算法 skill 与 quick helper，`tests/test_futu_skill.py` 与 `tests/skills/test_futu_skill.py` 主要覆盖 provider skill 的 metadata、SDK 初始化、options / fundamentals 行为，`tests/test_yfinance_skill.py` 也仍以具体 skill 实现与实例方法 patch 为主。因此，本轮更准确的记录方式不是继续把“tests 仍存在 direct import”笼统视作待统一收敛的问题，而是先把“运行时路径已完成最小收敛、测试层当前以 implementation-level unit test 保留为主”写清；其中 `tests/test_yfinance_skill.py` 是否还存在可再细分的 seam-like 断言，仍可留作后续单独甄别，但本轮不直接进入测试代码替换。

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
- 证据：`docs/baselines/current-architecture-baseline.md` 已把 deploy 现状拆分为 config / script defaults、human-readable deployment docs 与 baseline interpretation 三层，避免把静态表述直接压成单一运行真相。
  - `docs/baselines/current-architecture-baseline.md:110`
  - `docs/baselines/current-architecture-baseline.md:123`
  - `docs/baselines/current-architecture-baseline.md:127`
- 结论：**基本符合，但表述边界仍待收敛**
- 说明：基于当前对 `deploy/**`、`pyproject.toml`、`deploy/README.md` 与 baseline 文档的静态回读，本轮可先按三类归纳当前部署相关表述：其一，`deploy/ecosystem.config.js`、`deploy/supervisord.conf` 与 `deploy/deploy.sh` 中的路径、端口与命令更接近配置 / 脚本层默认值；其二，`deploy/README.md` 更接近面向人阅读的部署说明；其三，baseline 文档当前则负责把这两类静态证据分层记录，并把 `8000` / `8001` 端口指向与多套进程管理角色之间的关系保留为待确认项。因此，本轮更准确的收敛方式，不是把 PM2、supervisord、systemd、docker compose 压成单一路径，而是先把每类表述各自属于什么证据层级写清；本轮不直接进入部署配置修改。

## 5. 审计摘要
### 5.1 已符合
- root / `web/` / `src/` 三层规则入口已落位。
- 前端首页 route file 抽样与 API 边界方向基本符合局部规则。
- 后端 API 聚合入口与编排层分离方向基本符合局部规则。
- `src/skills/` 与顶层 `skills/` 的 framework / implementation 双轨语义，已被当前目录内容与主要引用方式基本支撑。
- 部署路径假设已在配置与脚本层被编码为静态前提。

### 5.2 待确认
- 前端共享层是否存在更隐蔽的 route 反向依赖。
- `tests/test_yfinance_skill.py` 中是否仍存在可从具体 skill 实现断言中继续拆出的 seam-like 测试子样本，仍需继续区分。
- 部署端口与进程模型表述中，哪些差异只是脚本默认值与文档叙述的口径不同，哪些已接近潜在配置口径冲突，仍需继续区分。

### 5.3 偏离但暂不迁移
- `src/cli.py` 直接触达 orchestrator、registry 与 LLM client，入口层耦合偏重，适合作为后续独立治理切片。
- `src/skills/` 与顶层 `skills/` 的 framework / implementation 双轨语义虽已被现状支撑，本轮也已先完成 `src/api/routes/symbols.py` 与 `src/backtest/engine.py` 两个最小运行时样本的收敛；补充回读后的测试样本则显示，当前剩余 direct implementation import 主要集中在 implementation-level unit test，暂不直接进入统一替换或物理迁移。
- `deploy/**` 内已同时存在 PM2、supervisord、docker compose 与 systemd 相关表述；当前先通过 docs/spec 收敛各自角色与证据层级，不直接进入部署整改或配置统一替换。

## 6. 后续候选治理切片
> 说明：以下候选切片延续自本文前序审计结果；其中“后端 CLI 入口收敛子任务”“前端 import 图审计子任务”“Skill 双轨语义核查子任务”“跨目录依赖 DAG 审计子任务”“部署路径假设核查子任务”“Skill 双轨消费方式文档收敛子任务”“部署端口与进程模型表述收敛子任务”已分别被前序轮次推进，且本轮已把测试层样本进一步收敛为“实现级单元测试保留为主、仅 `tests/test_yfinance_skill.py` 仍可继续甄别是否存在 seam-like 子样本”的范围，因此这里保留当前更适合继续推进的后续候选。

1. **YFinance 测试边界细分子任务（候选）**
   - 目标：在已确认 `tests/test_volume_profile.py`、`tests/test_gex.py`、`tests/test_futu_skill.py` 与 `tests/skills/test_futu_skill.py` 主要属于 implementation-level unit test 的基础上，只继续甄别 `tests/test_yfinance_skill.py` 中是否仍存在值得转向 wrapper / registry / service seam 的局部测试样本。
2. **部署配置角色分层子任务（候选）**
   - 目标：在不改部署配置的前提下，进一步梳理 PM2、supervisord、systemd、docker compose 在当前仓库中的角色边界，明确哪些属于配置默认值，哪些属于文档层说明，哪些需要后续单独治理。

## 7. 本轮结论
本轮补充审计以 Skill 测试层 direct implementation import 的边界判断为主。基于当前对 `tests/test_volume_profile.py`、`tests/test_gex.py`、`tests/test_yfinance_skill.py`、`tests/test_futu_skill.py` 与 `tests/skills/test_futu_skill.py` 的静态回读与关键样本引用，可以进一步把上一轮笼统写作“测试层 direct implementation import 仍然存在”的结论收窄为：当前剩余 direct import 测试样本多数仍属于 implementation-level unit test，而不是已确认需要继续向 framework / registry seam 收敛的运行时消费路径。其中，`tests/test_volume_profile.py` 与 `tests/test_gex.py` 直接验证算法 skill 与 quick helper，`tests/test_futu_skill.py` 与 `tests/skills/test_futu_skill.py` 主要覆盖 provider skill 的 metadata、SDK 初始化、options / fundamentals 行为，均更适合按实现级单元测试保留；`tests/test_yfinance_skill.py` 虽也主要围绕具体 skill 实现与实例方法 patch 展开，但是否仍包含可单独拆出的 seam-like 局部样本，仍可留作后续单独甄别。因此，相比上一轮“测试层 direct import 仍待继续区分”的记录方式，本轮更准确的收敛方式，是先把“运行时路径已完成最小收敛、测试层当前以实现级单元测试保留为主、仅个别样本仍待细分”写清；本轮不直接进入测试代码替换。


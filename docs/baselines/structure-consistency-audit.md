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
- 证据：`current-architecture-baseline.md` 已明确 `deploy/` 和 PM2 / deploy 脚本依赖现有顶层结构及固定路径假设。
  - `docs/baselines/current-architecture-baseline.md:108`
  - `docs/baselines/current-architecture-baseline.md:115`
  - `docs/baselines/current-architecture-baseline.md:127`
- 结论：**符合**
- 说明：本项结论复用既有 baseline 的部署基线，不构成本轮对 `deploy/` 文件的重新审计；它用于支持“当前阶段不应直接进入物理目录迁移”的判断。

## 5. 审计摘要
### 5.1 已符合
- root / `web/` / `src/` 三层规则入口已落位。
- 前端首页 route file 抽样与 API 边界方向基本符合局部规则。
- 后端 API 聚合入口与编排层分离方向基本符合局部规则。
- `src/skills/` 与顶层 `skills/` 的 framework / implementation 双轨语义，已被当前目录内容与主要引用方式基本支撑。
- 部署与运行链路仍依赖当前顶层结构，和“不立即迁移”的治理约束一致。

### 5.2 待确认
- 前端共享层是否存在更隐蔽的 route 反向依赖。

### 5.3 偏离但暂不迁移
- `src/cli.py` 直接触达 orchestrator、registry 与 LLM client，入口层耦合偏重，适合作为后续独立治理切片。
- `src/skills/` 与顶层 `skills/` 的双轨命名语义虽已被现状支撑，但直接 import implementation 的消费方式仍增加理解成本；当前先不进入物理收敛。
- `deploy/` 与 `pyproject.toml` 仍对当前顶层结构和稳定入口存在固定路径假设，因此后续若进入物理迁移，必须单独处理部署与打包链路影响。

## 6. 后续候选治理切片
> 说明：以下候选切片延续自本文前序审计结果；其中“后端 CLI 入口收敛子任务”“前端 import 图审计子任务”“Skill 双轨语义核查子任务”“跨目录依赖 DAG 审计子任务”已分别被前序轮次推进或在本轮完成最小核查，因此这里保留当前更适合继续推进的后续候选。

1. **Skill 双轨消费方式收敛子任务（候选）**
   - 目标：在不做物理迁移的前提下，进一步确认哪些调用路径应继续通过 framework registry 获取能力，哪些路径允许直接消费顶层 implementation，以降低双轨理解成本。
2. **部署路径假设核查子任务（候选）**
   - 目标：在不改部署脚本的前提下，系统梳理 `deploy/`、PM2 与 `pyproject.toml` 对当前仓库顶层结构和入口路径的固定假设，识别后续结构治理的高风险约束。

## 7. 本轮结论
本轮补充审计收敛的是跨目录依赖 DAG 这一子范围。基于当前对 `web/**`、`src/**`、`tests/**`、`deploy/**` 与 `pyproject.toml` 的目录级静态搜索及关键样本回读，尚未发现生产路径上明确的 `web -> src` 反向依赖证据；前端侧主要表现为 route files 对 `components`、`lib`、`i18n` 的单向消费，后端侧主要表现为 `api` / `cli` 对 `agents`、`skills`、`llm` 的入口型依赖，整体方向与现有边界规则基本一致。相较之下，更明确的结构约束来自 `deploy/` 与 `pyproject.toml` 对当前顶层结构和稳定入口的固定路径假设，因此可以把“跨目录依赖图是否满足可审计 DAG”从单纯待确认推进为“基于当前静态证据基本符合、但部署路径假设仍构成后续迁移约束”的结论；本轮不直接进入代码修复或目录迁移。


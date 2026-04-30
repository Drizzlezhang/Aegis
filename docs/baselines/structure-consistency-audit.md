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
- 证据：针对 `web/**/*.{ts,tsx}` 做了明显 import 模式的初步扫描，未发现从共享层反向依赖 `web/app/*` 的直接命中。
- 结论：**待确认**
- 说明：本轮只覆盖明显 import 模式，不覆盖动态导入、别名重导出或更完整的 import 图分析；不能直接得出“完全无反向依赖”的强结论。

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
- 证据：baseline 与 `src/CLAUDE.md` 已明确：`src/skills/*` 是 Skill Framework Layer，顶层 `skills/*` 是 Skill Implementation Layer。
  - `docs/baselines/backend-logic-boundary-rules.md:132`
  - `docs/baselines/backend-logic-boundary-rules.md:210`
  - `src/CLAUDE.md:25`
  - `src/CLAUDE.md:53`
- 结论：**偏离但暂不迁移**
- 说明：当前规则层面已经澄清双轨语义，但仓库现实中仍保留两套相近命名，属于结构认知债务；本轮不做物理收敛，只保留为后续治理候选。

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
- 部署与运行链路仍依赖当前顶层结构，和“不立即迁移”的治理约束一致。

### 5.2 待确认
- 前端共享层是否存在更隐蔽的 route 反向依赖。
- 跨目录依赖图是否已经满足可审计 DAG，而不只是抽样上未见明显冲突。

### 5.3 偏离但暂不迁移
- `src/cli.py` 直接触达 orchestrator、registry 与 LLM client，入口层耦合偏重，适合作为后续独立治理切片。
- `src/skills/` 与顶层 `skills/` 的双轨命名语义仍然增加理解成本；当前已通过规则澄清，但尚未通过结构收敛解决。

## 6. 后续候选治理切片
> 说明：以下候选切片延续自本文前序审计结果；其中仅“后端 CLI 入口收敛子任务”直接由本轮后端入口层依赖审计进一步强化。

1. **后端 CLI 入口收敛子任务**
   - 目标：把 `src/cli.py` 的入口职责收敛到参数解析、模式选择与输出编排，减少对 orchestrator / registry / LLM client 的直接耦合。
2. **前端 import 图审计子任务**
   - 目标：系统确认 `web/components`、`web/lib`、`web/i18n` 是否存在对 `web/app/*` 的反向依赖。
3. **Skill 双轨语义核查子任务**
   - 目标：梳理 `src/skills/*` 与顶层 `skills/*` 的实际引用方式，确认最小风险的后续治理顺序。
4. **跨目录依赖 DAG 审计子任务**
   - 目标：把当前抽样检查升级为更系统的依赖图核查，识别真正需要后续拆分的高风险边界问题。

## 7. 本轮结论
本轮补充审计只进一步收敛了后端入口层依赖边界这一子范围。基于当前对 `src/api/*` 的抽样与明显 import 模式扫描，尚未发现入口层直接触达 `src.llm` 或 `src.skills` framework 中心逻辑的明确证据；但这仍不替代全量 route 依赖图核查。相较之下，`src/cli.py` 直接触达 orchestrator、registry 与 LLM client 的证据更明确，因此可以作为后续独立治理切片候选；本轮不直接进入代码修复。

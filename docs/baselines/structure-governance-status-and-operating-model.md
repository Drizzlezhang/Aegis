# Structure Governance Status and Operating Model

## 1. Context
本文用于承接当前仓库结构治理阶段性结果，把已经完成的最小收敛事项、当前结构边界理解方式，以及后续开发与维护动作沉淀为一个长期可复用的说明入口。

本文不是新的单一真相源，也不替代以下事实来源：
- `docs/baselines/current-architecture-baseline.md`
- `docs/baselines/structure-consistency-audit.md`
- 根 `CLAUDE.md`
- `web/CLAUDE.md`
- `src/CLAUDE.md`

阅读顺序建议：
1. 先看 baseline，理解当前仓库真实结构与稳定入口。
2. 再看 audit，理解当前规则-现状差异、已符合项与暂不迁移项。
3. 最后看本文，理解“当前已经治理到什么程度”以及“后续开发如何继续维持结构一致性”。

## 2. What This Governance Round Completed
本轮治理不是物理目录迁移，也不是业务逻辑重构，而是在不改业务语义、UI 交互、API contract 与部署入口的前提下，先完成最小结构收敛与规则落位。

### 2.1 Rules entry points landed
已形成仓库级与目录级的最小规则入口：
- 根 `CLAUDE.md` 继续承载跨目录协作、风险控制与统一验证要求。
- `web/CLAUDE.md` 承载前端局部规则。
- `src/CLAUDE.md` 承载后端局部规则。

当前结论是：root / `web/` / `src/` 三层规则入口已经落位，当前阶段没有继续下钻更多二级 `CLAUDE.md` 的必要。

### 2.2 Runtime consumer paths minimally converged
当前仓库里，`src/skills/*` 与顶层 `skills/*` 的双轨语义已被明确区分：
- `src/skills/*`：Skill framework layer
- 顶层 `skills/*`：Skill implementation layer

在此基础上，本轮已完成两个最小运行时样本的收敛：
- `src/api/routes/symbols.py`
- `src/backtest/engine.py`

这两个运行时消费者已从 direct implementation import 收敛为通过 framework / registry 获取 skill 实例。当前更准确的结论不是“所有 direct import 都应消失”，而是“运行时消费路径优先通过 framework seam 收敛，测试层则继续按测试目的区分”。

### 2.3 Deployment expression levels narrowed in docs
本轮没有改部署配置，而是先把部署相关表述的证据层级区分清楚：
- `deploy/ecosystem.config.js`、`deploy/supervisord.conf`、`deploy/deploy.sh` 更接近 config / script defaults
- `deploy/README.md` 更接近面向人阅读的部署说明
- `docs/baselines/current-architecture-baseline.md` 负责把这些静态证据分层记录，并保留待确认项

当前不再把 PM2、supervisord、systemd、docker compose 压成单一部署真相，而是明确它们属于不同证据层级。

### 2.4 Skill test boundary conclusion narrowed
本轮对测试层 direct implementation import 的结论做了进一步收窄：
- `tests/test_volume_profile.py`
- `tests/test_gex.py`
- `tests/test_futu_skill.py`
- `tests/skills/test_futu_skill.py`

这些样本当前主要仍属于 implementation-level unit test，应以保留为主。

`tests/test_yfinance_skill.py` 中最后一个最小子样本也已完成最小收敛：
- 把 `test_get_ohlcv_caching` 从依赖私有调用细节的断言，收敛为公开结果稳定性断言
- 该文件仍整体属于 implementation-level unit test，不转写为 registry seam 或 wrapper seam 测试

因此，本轮更准确的治理结论是：
- 运行时路径已完成最小样本收敛
- 测试层当前以 implementation-level unit test 保留为主
- 只有极少数局部断言需要做最小去耦，不做一刀切替换

## 3. Current Repository Operating Model
### 3.1 Repository reality
当前仓库仍是单 Git 仓库下的前后端并存结构，不是标准 workspace monorepo：
- `web/`：Next.js 前端应用
- `src/`：Python 主业务源码
- `tests/`：Python 测试目录
- `deploy/`：部署脚本与进程配置

后续所有结构治理与新增开发，都应先接受这个现实，而不是假定仓库已经迁移到新的物理目录形态。

### 3.2 Responsibility boundaries
当前建议按以下职责边界理解目录：
- `web/`：页面、展示、前端 route orchestration、主题、i18n、前端 API consumption
- `src/api/*`：HTTP 入口、路由装配、协议接入
- `src/agents/*`：后端编排层与领域执行切片
- `src/skills/*`：Skill framework layer
- 顶层 `skills/*`：Skill implementation layer
- `src/llm/*`：模型访问层
- `tests/*`：按测试目标覆盖实现级、接口级或集成级验证
- `deploy/*`：部署配置、脚本与运行说明

### 3.3 Stable anchors
当前阶段应继续把以下入口视为稳定锚点：
- `src/api/main.py`
- `src/cli.py`
- `src/skills/registry.py`
- `web/lib/api.ts`
- 根 `CLAUDE.md`
- `web/CLAUDE.md`
- `src/CLAUDE.md`

后续治理优先围绕这些稳定入口做边界收敛，不贸然移动入口路径。

## 4. How To Continue Developing After Governance
### 4.1 Before adding new code
新增代码前先判断三件事：
1. 这是前端展示问题、后端入口问题、编排问题、framework 问题，还是 implementation 问题？
2. 新逻辑应该落在稳定入口之后的哪一层，而不是先想“放哪个文件方便”？
3. 这次改动是在继续收敛边界，还是在引入新的越层依赖？

### 4.2 Runtime consumers first respect framework seams
如果改动涉及运行时消费路径：
- API route、CLI、backtest、agent 等运行时调用方，优先通过 framework / registry / 编排层已有 seam 消费能力
- 不把运行时路径重新写回 direct implementation import
- 若确实需要新增 seam，优先在已有稳定入口模式附近补，而不是绕开现有 pattern

### 4.3 Implementation tests stay purpose-driven
如果改动涉及测试：
- 先判断测试目标是在验证具体 skill / helper 实现，还是在验证消费边界
- implementation-level unit test 可以继续 direct import concrete implementation
- 不因为“运行时路径应收敛”就把所有实现级单测一律迁成 registry seam / wrapper seam
- 只有当某个断言明显过度依赖私有调用细节、却本质在验证公开 contract 时，才做最小去耦

### 4.4 Avoid inventing future directory promises
当前阶段仍以“先收敛逻辑边界，再决定是否物理迁移”为主。
因此：
- 不把未来可能的目录形态写成当前承诺
- 不把 `feature/shared/foundation` 等未来方向当成现有目录现实
- 不在边界还不稳定时提前扩散更多局部规则文件

### 4.5 Treat docs by scope, not by convenience
新增说明文档时，优先判断作用域：
- baseline：描述当前真实结构与稳定入口
- audit：记录规则-现状差异、已符合项、偏离项与候选治理切片
- `CLAUDE.md`：记录稳定、通用、反复适用的协作与执行规则
- topic summary / operating guide：承接某轮治理结果与持续维护方式

不要因为写起来方便，就把局部阶段性结论回填成全局长期规则。

## 5. How To Maintain Structure Consistency
### 5.1 Use small governance slices
后续若继续治理，优先采用“小切片”方式推进：
- 先识别一个明确偏离点
- 先在 docs / baseline / audit 中收敛表述
- 只在事实与收益都足够明确时，再进入最小代码收敛
- 每个切片都应有独立验证，不把多个边界问题绑成一次大迁移

### 5.2 Prefer evidence-backed wording
更新结构相关文档时，优先使用以下证据：
- 现有 `CLAUDE.md` 规则
- baseline 中的仓库现实与稳定入口
- audit 中的已符合 / 待确认 / 偏离但暂不迁移
- 关键运行时样本与关键测试样本的最小回读

文档表述必须区分：
- 已完成
- 基本符合
- 待确认
- 偏离但暂不迁移

不要把“尚未发现问题”写成“问题不存在”。

### 5.3 Keep dependency direction visible
维护结构一致性时，重点看三类信号：
- 是否出现入口层反向依赖下层实现细节
- 是否出现 shared 层反向依赖 route / page 层
- 是否出现 framework layer 与 implementation layer 职责混写

只要出现这些信号，就应先把它作为独立治理切片记录，而不是在功能开发中顺手混改。

### 5.4 Reuse existing verification style
结构治理任务默认继续复用当前验证风格：
- 文档任务：交叉回读 baseline / audit / `CLAUDE.md`，确认事实一致
- 最小代码收敛：只跑目标测试或最小相关验证
- 不因为是结构治理就默认触发全仓大测试
- 不在没有证据的情况下声称“结构已完成统一治理”

## 6. Known Caveats And Deferred Items
截至当前阶段，以下内容仍不应写成“已完成治理”：

### 6.1 CLI entry coupling remains heavy
`src/cli.py` 当前仍直接触达 orchestrator、registry 与 LLM client，入口层耦合偏重。
这已足以构成后续独立治理切片，但当前仍属于“偏离但暂不修复”。

### 6.2 Frontend reverse dependency risk not fully disproved
当前只完成了对明显 import 模式的静态扫描，尚不足以证明前端 shared 层对 route 层“完全无反向依赖”。
因此更准确表述应是“基本符合”，而不是“彻底清零”。

### 6.3 Deployment truth remains layered, not unified
当前部署相关表述已完成“证据层级区分”，但尚未完成“单一路径统一”。
端口差异、进程角色差异、脚本默认值与文档口径差异，仍有待后续继续区分。

## 7. Recommended Default Workflow For Future Structure Tasks
后续若再做结构治理，默认工作流建议如下：
1. 先定位任务域与作用域：repo 级、前端局部、后端局部、部署表述、测试边界。
2. 先读现状与事实源，不直接改代码。
3. 先在 baseline / audit / 局部规则中收敛结论，再决定是否需要最小代码改动。
4. 代码改动只做最小样本，不把 docs 收敛直接扩展成大规模重构。
5. 每个切片都补最小验证，并把结论写清是“已完成”“待确认”还是“暂不处理”。

## 8. References
- `docs/baselines/current-architecture-baseline.md`
- `docs/baselines/structure-consistency-audit.md`
- `CLAUDE.md`
- `web/CLAUDE.md`
- `src/CLAUDE.md`

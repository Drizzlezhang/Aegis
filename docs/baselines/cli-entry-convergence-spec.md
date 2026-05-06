# CLI 入口收敛规格（最小实施前计划）

## 1. 文档定位
本文承接 `docs/baselines/structure-consistency-audit.md` 中已经确认的后端 CLI 入口层偏离问题，用于把下一轮结构治理任务收敛成可执行的最小规格。

本文目标不是立即改代码，而是先明确：
- `src/cli.py` 的目标职责边界
- 哪些直接依赖应从 CLI 入口层移出
- 后续收敛应按什么 stage 推进
- 下一轮执行任务的最小安全切片是什么

本文不直接承诺目录迁移，也不在本轮修改 CLI 行为、API contract、模型路由、部署或测试链路。

## 2. 规则来源
- `src/CLAUDE.md`
- `docs/baselines/backend-logic-boundary-rules.md`
- `docs/baselines/structure-consistency-audit.md`

其中需要复用的核心规则是：
1. `src/cli.py` 属于后端入口层，职责应收敛到参数解析、执行模式选择与结果输出编排。
2. 入口层不得直接承担复杂业务策略实现。
3. 入口层不得直接承担 Skill framework 中心治理逻辑。
4. 入口层不得直接触达模型客户端，应通过编排层或能力层间接使用模型访问能力。

## 3. 当前偏离点
根据现有审计证据，`src/cli.py` 当前存在以下直接依赖：
- 直接 import `Orchestrator`
- 直接 import `get_global_registry`
- 直接 import `get_llm_client`

对应路径上暴露出的偏离包括：
- `run_analysis()` 直接创建并调用 `Orchestrator`
- `list_skills()` 直接驱动 registry 做技能发现
- `check_health()` 直接初始化 LLM client，并直接触达技能发现逻辑

结论上，这些路径说明当前 CLI 入口层不只是“命令接入 + 输出编排”，而是直接触达了编排层、framework 层与模型访问层的构造/调用细节。

## 4. 目标职责边界
后续收敛后，`src/cli.py` 应只保留以下职责：
- 命令行参数解析
- 命令分发与执行模式选择
- 用户可见输出组织
- 退出码处理
- 对现有 `api` 命令保留入口触发职责；该路径不属于 stage 1 收敛目标

后续应从 CLI 入口层收敛出去的职责：
- 直接创建 `Orchestrator`
- 直接驱动 `SkillRegistry` / `get_global_registry`
- 直接初始化 LLM client
- 任何超出“入口适配 + 输出编排”的下层依赖构造细节

## 5. 最小目标形态
本轮规格只约束一个最小目标形态，不预先设计完整 application layer：

1. `src/cli.py` 继续保留为 CLI 入口文件。
2. `pyproject.toml` 中的 CLI entrypoint 保持不变。
3. 后续执行时，只允许引入一个**足够小的 CLI-facing backend boundary**，用于承接当前入口层不应直接触达的能力调用。
4. 该边界应提供粗粒度操作，而不是把下层细节重新暴露回 `cli.py`。

本规格不要求先把 API 与 CLI 抽成统一入口抽象，也不要求引入新的目录层级。

## 6. Stage 切分策略
### Stage 1：收敛最小高确定性路径
下一轮真正执行时，优先只处理以下两条路径：
- `list_skills()`
- `check_health()`

选择理由：
- 这两条路径的入口层越界最明确。
- 与 `run_analysis()` 相比，生命周期复杂度更低。
- 更适合作为第一轮收敛切片，不容易把任务放大成 orchestrator 架构重写。

Stage 1 的目标是：
- 让 CLI 入口不再直接驱动 registry
- 让 CLI 入口不再直接初始化 LLM client
- 不改变现有命令名、参数和用户可见行为

### Stage 2：再评估分析路径
`run_analysis()` 是否进入同一轮收敛，不在本规格中预先绑定为 stage 1。

进入 stage 2 前，需要再次确认：
- `Orchestrator` 初始化生命周期是否能在不改变行为的前提下被安全封装
- 分析输出路径是否会因为收敛边界而引发额外 contract 讨论
- 是否仍能保持“小切片、低外溢”的原则

如果这些条件不满足，应把 `run_analysis()` 继续留作后续单独切片，而不是硬并入第一轮实现。

## 7. 下一轮执行范围
下一轮 `/execute-plan` 的推荐范围：
1. 仅为 Stage 1 设计并落地最小收敛实现。
2. 只允许修改与 `list_skills()` / `check_health()` 路径直接相关的文件。
3. 不同时清理 `run_analysis()`、API 入口或更广泛的 registry / llm 依赖。
4. 不进行无关重构。

## 8. 验收标准
Stage 1 执行完成后，至少应满足：

### 8.1 结构验收
- `src/cli.py` 不再直接 import：
  - `src.skills.registry.get_global_registry`
  - LLM client factory（即当前用于初始化模型客户端的直连入口）
- 本轮若仍保留 `Orchestrator` 相关 import，只能出现在未纳入 stage 1 的分析路径上，不得新增新的越层直接依赖。

### 8.2 行为验收
- CLI 命令集合不变。
- `list-skills` 的用户可见输出语义不变。
- `health` 的用户可见输出语义不变。
- `status`、`reload-config`、`version`、`api` 行为不受影响。

### 8.3 范围验收
- 不修改 API contract。
- 不修改模型路由行为。
- 不引入目录迁移。
- 不把本轮执行扩展成通用 backend application layer 重构。

## 9. 验证建议
下一轮执行完成后，至少验证：
1. 静态检查 `src/cli.py` import，确认 stage 1 目标依赖已移出入口层。
2. 运行 CLI 相关命令，确认：
   - `list-skills`
   - `health`
   - `status`
   - `version`
3. 若执行中新增了小型封装模块，应回读其公开接口，确认没有把 registry / llm 的构造细节重新暴露给 `cli.py`。
4. 回看 `git diff --name-only`，确认改动没有无意扩展到 API、agents、skills、llm 的广泛实现文件。

## 10. 风险与回滚关注点
### 风险
- 容易滑向“顺手设计一个通用 application layer”，导致范围膨胀。
- 若把 `run_analysis()` 一并纳入第一轮，可能引发 `Orchestrator` 生命周期与输出路径问题。
- 如果只移动代码位置、不改变依赖方向，可能形成“表面收敛、实际仍越层”的假收敛。

### 回滚关注点
- Stage 1 应保持小切片，确保后续若方向不合适，可以只回退 CLI 收敛相关文件。
- 不要把 `list_skills()` / `check_health()` 收敛与其它入口层清理混在同一提交里。
- 若执行中发现 `health` 路径天然需要重新定义健康检查 contract，应先停下来重新规划，而不是在同一轮里扩展需求。

## 11. 本规格结论
当前最合理的下一执行任务，不是直接重写 `src/cli.py` 全部命令路径，而是先基于本规格完成 Stage 1：收敛 `list_skills()` 与 `check_health()` 的入口层直接依赖。只有在这一最小切片验证稳定之后，再决定是否继续推进 `run_analysis()` 的收敛。
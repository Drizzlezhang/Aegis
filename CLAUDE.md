# Aegis-Trader 项目契约

## 1. 项目定位
- Aegis-Trader 专注美股正股与期权（LEAPS Call、Bull Spreads、Covered Call）的左侧抄底策略。
- 系统形态是面向研究、分析、策略生成的 Multi-Agent 量化交易系统。
- 核心标的：`QQQ`、`SPY`、`NVDA`、`MSFT`、`AAPL`、`PLTR`、`NFLX`、`INTC`、`TSM`、`TSLA`、`KO`。
- 优先关注：支撑位建仓、期权策略、多维支撑计算、机构级估值分析。

## 2. 目录与架构边界
```text
TradeAgent/
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── src/
│   ├── skills/
│   ├── agents/
│   ├── llm/
│   └── utils/
├── skills/
│   ├── data_sources/
│   └── algorithms/
├── web/
├── tests/
└── deploy/
```

- `src/skills/`：Skill 基类、注册与加载逻辑。
- `skills/`：外部 Skill 模块，每个 Skill 必须有 `skill.yaml` 与 `skill.py`。
- `src/agents/`：Agent 实现。
- `src/llm/`：模型路由与客户端。
- `web/`：Next.js 仪表盘。
- `tests/`：单元、集成、API、端到端测试。
- `deploy/`：部署配置。

## 目录级规则分层（Phase 2 最小落位）
- 根 `CLAUDE.md` 继续承载全局项目契约、跨目录协作规则、风险控制与统一验证要求。
- `web/CLAUDE.md` 承载仅对前端目录生效的局部规则；进入 `web/` 范围工作时，应同时遵守根规则与 `web` 局部规则。
- 当前阶段只做规则落位，不做物理目录迁移；`feature/shared/foundation` 等未来结构仅作为职责参考，不视为已承诺目录形态。
- 当前阶段不继续下钻到 `app/`、`components/`、`lib/` 等二级目录 `CLAUDE.md`，除非后续阶段单独确认目录边界已稳定。

## 开发规范
### Skill 接口
- 每个 Skill 必须包含 `skill.yaml` 元数据和 `skill.py` 实现
- Skill 基类定义在 `src/skills/base.py`
- 通过 `SkillRegistry` 动态发现和加载

### 架构硬约束
- 垂直分层：`Data -> Analysis -> Strategy -> Memory`。
- 水平隔离：Agent 之间不直接耦合，通过 Orchestrator 协调。
- 通过接口交互，不依赖跨模块内部实现。
- 避免循环依赖，保持依赖图为 DAG。
- 修改跨模块接口时，把接口变更作为独立任务处理。

## 3. Think Before Coding
- 先澄清目标、边界、成功标准，再动手。
- 有歧义先问关键问题，不静默脑补。
- 有多种合理方案时，先给 tradeoff，再给推荐。
- 先理解问题，再修改代码。
- 先找现有实现、模式、工具，再决定是否新增。

### 默认推进顺序
1. 定位任务域与作用域。
2. 先读现状，后改代码。
3. 先给计划，再执行非 trivial 改动。
4. 执行后给验证方式与结果。
5. 完成后给 review / 收尾建议。

### 任务拆分规则
1. 按模块边界拆分。
2. 先完成读，再开始写。
3. 接口先行。
4. 每个子任务都应可独立验证。

## 4. Simplicity First
- 只做当前任务要求内容，不加无关功能、抽象、配置项。
- 优先简单方案，不为一次性需求设计未来扩展。
- 不为假想场景补额外错误处理、回退逻辑或 feature flag。
- 三行重复通常比提前抽象更好。
- 不新增无必要文件；优先复用现有文件与现有模式。

## 5. Surgical Changes
- 不修改未读过文件。
- 不顺手重构、不统一风格、不清理无关代码。
- 每处改动都应能追溯到当前任务目标。
- 优先根因修复，不用临时绕过掩盖问题。
- 确认无用代码后可直接删除；不留“removed”式兼容痕迹。
- 不新增注释、docstring、类型声明，除非本次改动确实需要。

### 文件与代码粒度约束
- 源码文件尽量不超过 300 行；测试文件尽量不超过 500 行。
- 函数尽量不超过 50 行。
- 类尽量不超过 15 个方法。
- 优先垂直拆分，避免把单文件做大。

## 6. Workflow & Verification
### 模型与上下文
- 本项目统一按 `deepseek3.2` 开发协作约束组织工作流；用户自行切换模型，Claude 不主动提示切换。
- 单次读取不超过 500 行。
- 单次并行读取不超过 3 个文件。
- 单轮工具调用不超过 5 个。
- 优先 `Edit`，避免全文件重写。
- 复杂任务优先拆子任务；`/compact` 只是最后手段。

### 输出与执行要求
- 默认使用中文。
- 结论先行，表达简洁。
- 引用代码位置用 `file_path:line_number`。
- 不确定时明确写假设。

### 完成时必须补充
- 如何运行相关测试。
- 是否需要 lint / typecheck / build。
- 是否有关键手动验证路径。
- 是否有高风险回归点。
- 是否有临时调试代码未清理。
- 是否有无关文件被修改。
- 是否建议整理 commit / PR 描述。

### 项目验证重点
- Skill 加载器可动态发现和加载。
- yfinance Skill 获取 `QQQ` OHLCV 非空。
- Volume Profile 的 `POC/VAH/VAL` 计算正确。
- GEX Wall 识别结果合理。
- 端到端分析报告可输出。
- Docker 容器可在 AWS Singapore 目标环境启动。

## 7. Tool / Plugin Rules
### superpowers
- superpowers 用于 planning、execution、verification、debugging、review、finish-branch 等流程型能力。
- 必须区分自动调用与手动调用。

#### 自动调用
仅在触发条件清晰、收益稳定时自动调用，典型包括：
- `superpowers:writing-plans`
- `superpowers:executing-plans`
- `superpowers:verification-before-completion`
- `superpowers:systematic-debugging`
- `superpowers:using-superpowers`

适用原则：
- 任务阶段明确。
- 触发条件低歧义。
- 不会明显改变用户工作节奏。

#### 手动调用
以下 skill 默认手动调用，需用户明确要求或场景强匹配：
- brainstorming / design consultation 类
- code review / receiving review 类
- finishing branch / branch strategy 类
- writing skills / skill authoring 类
- 任何高成本、强主观、会显著改变流程节奏的 skill

#### superpowers 冲突规则
- 项目 `CLAUDE.md` 规则优先于 skill 默认说明。
- 自动调用不能绕过计划、验证、风险确认。
- 不把所有 superpowers skill 都变成自动。

### gstack
- gstack 提供更完整的规划、评审、QA、ship、browser 工作流。
- 项目采用 gstack team/optional 模式接入。
- gstack 用于补强工作流，不替代项目治理规则。

#### gstack 使用规则
- 优先把 gstack 用在设计评审、计划复核、QA、ship 前检查。
- 仅在需要真实网页调研或浏览器验证时使用 `/browse`。
- gstack 给出的流程建议，必须服从本文件的任务拆分、风险控制、accept-edits 约束。
- 若 gstack 建议与项目规则冲突，以本文件为准。

#### 推荐 gstack 命令
- `/office-hours`
- `/plan-ceo-review`
- `/plan-eng-review`
- `/review`
- `/qa`
- `/ship`
- `/browse`

### 协作分工
- gstack：偏阶段编排、设计评审、QA、ship。
- superpowers：偏技能型执行、验证、调试、子任务组织。
- 两者都必须遵守：先计划、按模块拆分、验证闭环、风险确认。

### caveman 模式
- 长会话、调试、大文件任务默认适合 caveman 模式。
- 安全确认、高风险动作、顺序敏感步骤必须切回清晰表达。

## 8. 前端专项规范
### 双语兼容
- 所有用户可见前端界面默认支持 `zh-CN` 与 `en`。
- 新增页面、组件、按钮、表单、状态提示时，必须同步补齐中英文文案。
- 用户可见文案统一走 i18n message，不在组件里硬编码语言。
- ticker、指标缩写、策略术语保留英文原样。
- 前端改动完成后，至少检查中英文两种 locale 的关键页面。

### 行情颜色语义
- 涨跌语义统一采用中国市场习惯：上涨红、下跌绿。
- 仅价格变化、指数变化、涨跌幅、市场方向场景适用。
- 优先复用 `web/lib/change-color.ts`。
- 不在组件里继续硬编码涨跌 class。
- 策略推荐、系统状态、成功失败状态不适用该规则。

## 9. 风险控制
以下情况先提醒再继续：
- 修改全局配置。
- 修改权限、认证、token、hook、MCP、CI/CD 配置。
- 可能覆盖用户未提交改动。
- 可能影响多个项目共享行为。
- 需要联网、登录、访问外部系统或调用第三方服务。
- 需要执行高风险、不可逆或对外可见动作。

### 高风险动作必须先确认
- 删除文件/目录。
- 修改 `pyproject.toml`、Dockerfile、CI/CD 等全局配置。
- 修改 `.env`、`config.py` 中敏感配置。
- 跨模块接口变更。
- 单次修改超过 5 个文件或 500 行。
- 数据库/存储 schema 或数据清理操作。
- `git reset --hard`、`git clean -f`、强推、跳过 hooks 等破坏性动作。

## 10. accept-edits 安全规范
任何 `Edit` 执行前，必须说明：
1. 修改目标。
2. 修改原因。
3. 影响范围。
4. 回退方式。

禁止：
- 自动修改未读过文件。
- 自动运行会破坏数据命令。
- 自动添加/删除依赖。
- 自动执行会覆盖未保存改动的测试或脚本。

建议：
- 任务开始前检查 `git status`。
- 大改前创建临时分支。
- 修改后给明确回退命令。

<!-- devkit-managed:start version=1 generated_at=2026-05-14T12:56:48.090Z -->
## DevKit Configuration

This section is managed by `devkit-init`. Do not edit manually.

### Installed Skills
- devkit-init: project bootstrap, audit, adopt
- devkit-go: 7-stage development workflow

### Enabled Plugins
- superpowers
- gstack

### Project Meta
- language: [python, shell, typescript]
- framework: [fastapi, nextjs]
- scale: L
- internal: false

### Workflow Conventions
- 触发 devkit-go 进入 7 阶段流程
- _meta.yaml schema_version: 2
- STATE.md 字段顺序锁定(详见 templates/STATE.md)
<!-- devkit-managed:end -->

## 13. 4-Clone 并行开发治理规则

### 13.1 Territory Principle（领地原则）

每个 feature 分支只能修改其领地内的文件，禁止跨领地修改：

| Clone 目录 | 分支 | 领地 |
|---|---|---|
| `aegis-data/` | `feature/data-pipeline` | `src/agents/data_harvester/`, `skills/`, `src/config.py`, `tests/agents/test_data*`, `tests/skills/` |
| `aegis-brain/` | `feature/analysis-brain` | `src/agents/quant_brain/`, `src/agents/strategy_exec/`, `src/agents/debate/`, `tests/agents/test_quant*`, `tests/agents/test_strategy*` |
| `aegis-memory/` | `feature/memory-position` | `src/agents/aegis_memory/`, `src/agents/position_monitor/`, `tests/agents/test_memory*`, `tests/agents/test_position*` |
| `aegis-ui/` | `feature/frontend-skills` | `web/`, `src/api/`, `tests/api/`, `tests/e2e/` |

### 13.2 Shared File Rules（共享文件规则）

以下文件被多个领地共享，必须遵守修改协议：

| 共享文件/目录 | 规则 |
|---|---|
| `src/models/*.py` | **只允许新增文件**，不修改已有文件 |
| `src/models/__init__.py` | **只允许在末尾追加** `from .xxx import ...` |
| `src/agents/orchestrator.py` | **只通过 `register_agent()` 接入**，不修改 Orchestrator 内部逻辑 |
| `src/agents/__init__.py` | **只允许在末尾追加** import 语句 |
| `CLAUDE.md` | **禁止修改**，只有 main 分支管理员可更新 |

### 13.3 Merge Order（合并顺序）

分支合并到 main 的顺序严格遵循依赖链：

```text
feature/data-pipeline → feature/analysis-brain → feature/memory-position → feature/frontend-skills
```

- 上游未 merge，下游不得开始 rebase。
- 每次只允许一个分支先 merge，其他分支必须在最新 main 上同步后再继续开发。
- 若共享文件协议被破坏，必须停止并由 main 分支管理员统一协调。

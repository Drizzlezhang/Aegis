# AGENTS.md

<!-- devkit-managed:start version=1 generated_at=2026-05-16T10:17:36.971Z -->
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

## Trae CLI Collaboration Rules

### Source of Truth
- 根 `CLAUDE.md` 是本仓库的主项目契约；Trae CLI 与 Claude Code 都必须遵守。
- `web/CLAUDE.md` 仅作用于 `web/` 目录；前端任务需同时遵守根规则与该局部规则。
- `.devkit/project.yaml` 是 DevKit 项目元信息缓存；若技术栈、依赖锁文件或远端变化，应先运行 `/devkit-init` 巡检并同步。

### Skill Usage
- 长流程需求、跨模块实现、需要 SPEC / DESIGN / PLAN / VERIFY 闭环时，使用 `/devkit-go`。
- 初始化、巡检、Trae/Claude 协作配置同步时，使用 `/devkit-init`。
- `.specs/` 是 devkit-go 的唯一产物目录，不要把阶段产物写到其他位置。

### Project Boundaries
- 后端主栈：Python 3.12、FastAPI、Multi-Agent 量化交易系统。
- 前端主栈：Next.js、React、TypeScript，位于 `web/`。
- 前端用户可见文案必须保持 `zh-CN` / `en` 双语兼容。
- 行情涨跌颜色遵循中国市场习惯：上涨红、下跌绿，优先复用 `web/lib/change-color.ts`。

### Internal Tooling
- 当前仓库 remote 指向 GitHub，`.devkit/project.yaml` 标记为非字节内部项目。
- 不要默认安装或启用 `bytedcli`；只有出现明确字节内部强信号或用户显式要求时再规划。

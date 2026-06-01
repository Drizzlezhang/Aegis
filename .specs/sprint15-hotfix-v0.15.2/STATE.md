<!-- STATE.md schema_version: 1 -->
<!-- 字段顺序固定,模型新增内容必须落在已有段落内,禁止打乱顺序 -->

# State

## Current
- **change_id**: sprint15-hotfix-v0.15.2
- **size**: L
- **current_stage**: 3-PLAN
- **status**: in_progress
- **updated_at**: 2026-05-31T20:00:00+08:00

## Next Action
Size L 需经过 post-plan gate 确认后再进入 4-BUILD。按 Wave 1→5 顺序执行，每个任务带 verify 命令。

## Open Questions
- [x] F4 删除 paper 后 position_monitor 是整文件删还是改对账 BacktestStore？→ **改对账 BacktestStore**
- [x] F4 删除 paper 后 strategy_exec 输出改为 emit StrategySignalEvent，EventBus 是否需要新增事件类型？→ **需要新增 StrategySignalEvent**
- [x] F2 LLM 收敛后 governance middleware 测试需要多大改动？→ **对齐缩减到单 provider 规模**

## Risks
- F4 牵连面最大，paper 被 position_monitor / portfolio_service / event_bus / 宪法 guard 深度耦合，删它要逐项处理下游
- 删 paper 后 strategy_exec 输出无处去，需改为 emit StrategySignalEvent
- position_monitor 与 paper 强绑定，删后无替代，允许整文件删留 TODO
- 前端删登录后路由守卫漏改可能导致某些页面 404
- 侧边栏修改可能破坏 mobile 响应式

## Recent Changes
- [2026-05-31T19:45:00+08:00] 0-CHANGE → created proposal.md, _meta.yaml, STATE.md
- [2026-05-31T19:50:00+08:00] 1-SPEC → drafted requirements.md with 5 sub-requirements, ACs with verification methods
- [2026-05-31T19:55:00+08:00] 2-DESIGN → completed design.md with ADRs for F1-F5, file-level change lists
- [2026-05-31T20:00:00+08:00] 3-PLAN → tasks.md created with 5 waves, 28 atomic tasks, each with verify command

## Notes
- 基线分支：sprint15-hotfix-v0.15.1.1（tag v0.15.1.1）
- 目标分支：sprint15-hotfix-v0.15.2
- 本次只做减法 + 配置外置 + 入口补齐，不写新业务逻辑
- 真实券商账户只读同步留给 sprint16

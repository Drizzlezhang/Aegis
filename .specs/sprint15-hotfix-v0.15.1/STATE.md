<!-- STATE.md schema_version: 1 -->
<!-- 字段顺序固定,模型新增内容必须落在已有段落内,禁止打乱顺序 -->

# State

## Current
- **change_id**: sprint15-hotfix-v0.15.1
- **size**: L
- **current_stage**: 3-PLAN
- **status**: in_progress
- **updated_at**: 2026-05-30T10:50:00+08:00

## Next Action
进入 4-BUILD，从 Wave 1 T01 开始实现 LLM 治理链修复。

## Open Questions
- [ ] P0-4 宪法对齐：选路线 A（白名单 grep）还是路线 B（重命名方法）？默认路线 A
- [ ] 多 worker 共享 broker 状态：是否需要引入 Redis？默认标注"仅支持单 worker"

## Risks
- LLM 治理链修复可能影响现有 LLM 调用路径（Budget 异常不再被吞）
- EventBus 生命周期变更可能影响现有测试（需全局 start/stop）
- PaperBroker 方法签名变更（若选路线 B）影响面大
- 覆盖率从 25% 补到 40% 需要大量新测试

## Recent Changes
- [2026-05-30T10:30:00+08:00] 0-CHANGE → created proposal.md, _meta.yaml, STATE.md
- [2026-05-30T10:35:00+08:00] 1-SPEC → drafted requirements.md with 14 FR, 17 AC, all with verification methods
- [2026-05-30T10:45:00+08:00] 2-DESIGN → completed design.md with 6 domains, 5 ADRs, API/data model specs
- [2026-05-30T10:50:00+08:00] 3-PLAN → tasks.md with 30 tasks across 6 waves, all with verify commands

## Notes
需求来源：`/Users/bytedance/Downloads/sprint15-fix.md`
工作分支：从 `sprint15-final-integration` 拉 `sprint15-hotfix-v0.15.1`
每个修复点 1 个 commit，前缀 `hotfix(sprint15):`

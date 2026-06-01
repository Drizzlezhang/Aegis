<!-- STATE.md schema_version: 1 -->
<!-- 字段顺序固定,模型新增内容必须落在已有段落内,禁止打乱顺序 -->

# State

## Current
- **change_id**: sprint16-branch-B-signals
- **size**: M
- **current_stage**: 6-SHIP
- **status**: completed
- **updated_at**: 2026-06-01T11:30:00+08:00

## Next Action
push to remote / create PR

## Open Questions
- [ ] Polymarket Gamma API 是否需要 API key（确认免费 tier 限制）
- [ ] X adapter 走 Apify 还是 RapidAPI scraper（需确认可用性）
- [ ] Macro News 用 GDELT 2.0 还是 NewsAPI（免费 tier 日调用量限制）

## Risks
- 外部 API 不可用或限流导致 adapter 返回空（已容错：返回空 list + warning 日志）
- X scraper API 可能收费或停服（adapter 初始化为可选，配置不存在时跳过）
- GDELT tone 阈值可能需调参（当前默认 >1 / <-1）

## Recent Changes
- [2026-06-01T10:45:00+08:00] 0-CHANGE → proposal.md created, Size=M, stages=0→1→2→3→4→5→6
- [2026-06-01T10:50:00+08:00] 1-SPEC → requirements.md created with 7 FRs + 4 NFRs + 8 ACs
- [2026-06-01T10:55:00+08:00] 2-DESIGN → design.md created with 3 adapters + SignalCollector + 5 ADRs
- [2026-06-01T11:00:00+08:00] 3-PLAN → tasks.md created with 8 tasks in 4 waves
- [2026-06-01T11:05:00+08:00] 4-BUILD → Wave 1: B1 Polymarket, B2 X, B3 Macro News adapters
- [2026-06-01T11:10:00+08:00] 4-BUILD → Wave 2: B4 SignalCollector + SignalReceivedEvent
- [2026-06-01T11:15:00+08:00] 4-BUILD → Wave 3: B5 replace mock /api/signals
- [2026-06-01T11:20:00+08:00] 4-BUILD → Wave 4: B6 integration test (9 tests)
- [2026-06-01T11:25:00+08:00] 5-VERIFY → 50 tests pass, constitution grep pass, all 8 ACs verified
- [2026-06-01T11:30:00+08:00] 6-SHIP → 8 commits on sprint16-branch-B-signals, completed

## Notes
Sprint16 Branch B: Signal Sources (Polymarket + X + Macro News)。基于 Branch A 契约接入 3 个外部信号源。需求文档来源: /Users/bytedance/Downloads/branch_B_signals.md

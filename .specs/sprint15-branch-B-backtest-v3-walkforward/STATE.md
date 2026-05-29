<!-- STATE.md schema_version: 1 -->

# State

## Current
- **change_id**: sprint15-branch-B-backtest-v3-walkforward
- **size**: L
- **current_stage**: 4-BUILD
- **status**: in_progress
- **updated_at**: 2026-05-29T11:20:00+08:00

## Next Action
T01: CostModel 抽象 — 佣金实现（FixedCommission / PercentCommission / TieredCommission）

## Open Questions
- [ ] Walk-forward 性能是否达标（需 B13 提前验证）
- [ ] 与 Branch C CostModel 接口对齐（Day 4 前）
- [ ] 5m/1m 数据获取依赖 data_harvester 已有能力

## Risks
- Walk-forward 性能不达标（>10min/年）→ B13 提前到 Wave 1 末验证
- timeframe=1m 数据量爆内存 → 单元测试加 4GB 内存限制
- MC 计算耗时长 → 默认 N=1000，大数据时支持采样
- 与 Branch C CostModel 接口分歧 → Day 4 前对齐 contract

## Recent Changes
- [2026-05-29T11:15:00+08:00] 3-PLAN → tasks.md created: 16 tasks × 6 waves, each with verify command + read/write files + dependencies
- [2026-05-29T11:00:00+08:00] 2-DESIGN → design.md created: 6 new modules, 4 API endpoints, 3 CLI commands, 7 dataclasses, 3 ORM models, 6 ADRs
- [2026-05-29T10:30:00+08:00] 1-SPEC → requirements.md created: 16 FR, 47 AC, 6 user stories, 5 NFR, 9 edge cases
- [2026-05-29T10:00:00+08:00] 0-CHANGE → proposal.md created, size=L, 13 tasks × 6 waves

## Notes
分支: sprint15-branch-B-backtest-v3-walkforward
基于: master @ af07882
依赖: 软依赖 Branch A (稳定基线)
阻塞: Branch C (CostModel 复用) / Branch F (回测面板)

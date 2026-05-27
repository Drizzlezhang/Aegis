<!-- STATE.md schema_version: 1 -->
<!-- 字段顺序固定,模型新增内容必须落在已有段落内,禁止打乱顺序 -->

# State

## Current
- **change_id**: sprint12-phase-config
- **size**: S
- **current_stage**: 6-SHIP
- **status**: in_progress
- **updated_at**: 2026-05-27T12:45:00+08:00

## Next Action
commit + push

## Open Questions
- [x] 当前 DEFAULT_WEIGHTS 是 5 维，spec 要求 7 维。是否扩展为 7 维？ → **决定: 保持 5 维。velocity/acceleration scorer 不存在，属于新功能，不在本次范围。**
- [x] `_compute_all_dimensions()` 需要 velocity 和 acceleration 的 scorer 方法 → **不实现，保持 5 维。**

## Risks
- `_determine_phase()` 当前使用硬编码阈值（70/30/60/40），需替换为配置阈值 — 已完成

## Recent Changes
- [2026-05-27T12:45:00+08:00] 4-BUILD + 5-VERIFY → 3 files modified, config tests 12/12 pass, all ACs verified
- [2026-05-27T12:30:00+08:00] 1-SPEC → created requirements.md with 5 FRs, 14 ACs, boundary scenarios, out-of-scope
- [2026-05-27T12:00:00+08:00] 0-CHANGE → created proposal.md, _meta.yaml, STATE.md

## Notes
- 基于 `/Users/bytedance/Downloads/sprint12-branch-c-config.md` 创建
- 分支：feat/phase-predictor-config（已存在）
- phase_predictor.py 已存在（5 维 Wyckoff 引擎，450 行）
- TrendPhaseResult 已有 low_volatility_override 字段
- DEFAULT_WEIGHTS 当前为 5 维 ClassVar

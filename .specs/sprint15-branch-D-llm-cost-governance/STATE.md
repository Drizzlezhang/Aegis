<!-- STATE.md schema_version: 1 -->
<!-- 字段顺序固定,模型新增内容必须落在已有段落内,禁止打乱顺序 -->

# State

## Current
- **change_id**: sprint15-branch-D-llm-cost-governance
- **size**: M
- **current_stage**: 3-PLAN
- **status**: in_progress
- **updated_at**: 2026-05-29T00:00:00+08:00

## Next Action
进入 4-BUILD，按 Wave 顺序实现 D1-D9，每 task 独立 commit（Conventional Commits: feat(llm): ...）

## Open Questions
- [ ] 现有 LLM 调用入口有哪些？需确认所有调用点以插入中间件
- [ ] SQLite 缓存后端是否复用 HistoricalCache 模式？

## Risks
- 中间件链接入后破坏现有 LLM 调用行为 → D1 单独 commit，跑全量 debate / quant_brain 测试验证
- Cache 误命中（prompt 微小差异未捕获）→ D3 hash 必须包含 system_prompt / temperature / model 全部参数
- Budget 阻断导致关键流程失败 → D5 提供 bypass_budget 标志，critical agent 可豁免
- Prompt 重组破坏既有调用 → D6 渐进式迁移，旧 prompt 文件保留 deprecated 标记 1 个 Sprint

## Recent Changes
- [2026-05-29T00:00:00+08:00] 0-CHANGE → created proposal.md, _meta.yaml, STATE.md
- [2026-05-29T00:00:00+08:00] 1-SPEC → drafted requirements.md (9 FR, 12 AC, 7 edges, 4 NFR)
- [2026-05-29T00:00:00+08:00] 2-DESIGN → completed design.md (middleware chain, 10 components, 4 APIs, data model, config)
- [2026-05-29T00:00:00+08:00] 3-PLAN → created tasks.md (9 tasks, 6 waves, verify commands, risk tasks, rollback)

## Notes
- 基础分支: master @ af07882
- 分支约束: 不替换现有 LLM provider 实现，仅在调用链插入中间件
- 治理层可一键关闭: config.llm.governance.enabled = false
- 复用 Sprint 14: AlertEngine + EventBus + Prometheus
- 导出给 F: /api/llm/usage, /api/llm/budget, /api/llm/cache-stats JSON schema

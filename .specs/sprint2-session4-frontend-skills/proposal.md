# Change: sprint2-session4-frontend-skills

## 概述
在 `aegis-ui` 领地继续 Sprint 2 Session 4 前端与技能迭代，交付：
1) SSE 生命周期修复（AbortController + stream cancel）
2) SymbolSearch 组件替换 AnalyzeForm 硬编码 symbol 列表
3) AnalyzeForm/SymbolSearch/DebatePanel 的 i18n 覆盖补全与占位符插值
4) DebatePanel 解析 `analysisReport` 中 Investment Debate 文本并展示结论
5) BSM Skill 增加 implied volatility 求解（Newton-Raphson + bisection fallback）
6) SSE `executionTime` 修复为每 symbol 真实耗时
7) 前后端测试升级与回归验证

## 动机
Sprint 1 已交付流式进度与 BSM 基础定价，但仍存在生命周期泄漏、AnalyzeForm 可用性不足、i18n 覆盖不足、辩论信息不可见、BSM 缺少反解能力、测试粒度不足等问题，阻塞 Sprint 2 合并质量线。

## 影响范围
- 前端：`web/components/`, `web/i18n/`, `web/lib/`, `web/tests/`
- Skill：`skills/algorithms/bsm_pricer/`
- API 路由：`src/api/routes/analyze_stream.py`
- 后端测试：`tests/test_bsm_pricer.py`, `tests/api/test_analyze_stream.py`
- 不触达：`src/agents/`, `src/llm/`, `src/config.py`, `src/agents/orchestrator.py`, `CLAUDE.md`

## 验收目标
1. SSE 在组件卸载时可中断，无卸载后状态更新风险。
2. AnalyzeForm 支持搜索/自定义输入 symbol，去重与上限控制可用。
3. AnalyzeForm 结果区可展示 DebatePanel（可解析时展示，不可解析时静默）。
4. i18n 补齐 AnalyzeForm + SymbolSearch + DebatePanel 文案，支持模板插值。
5. BSM 支持 IV 反解，覆盖 ATM round-trip、deep OTM、无效价格场景。
6. `executionTime` 返回真实每 symbol 耗时。
7. 相关 pytest/vitest/type/build 验证通过。

## Size: L
## 推断依据
- 范围：跨 `web + skills + src/api + tests` 多模块联动。
- 关键词：`feature + test upgrade + algorithm extension`，非单点修复。
- 预估文件数：10+，含新组件、新工具、新测试。
- 风险：SSE 生命周期、报告解析鲁棒性、IV 数值稳定性、前端回归面较宽。
- 基线：`.devkit/project.yaml` 明确 `project.scale: L`，与本次任务复杂度一致。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

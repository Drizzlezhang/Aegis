# Change: add-frontend-sse-bsm-skill

## 概述
在 `aegis-ui` 领地内交付 3 类能力：SSE 分析进度可视化组件、BSM 期权定价 Skill、对应前后端测试与验证脚本。

## 动机
当前分析页仅有简单 loading 状态，缺乏可观测进度；期权策略缺少可复用定价引擎；测试覆盖不足以保障 SSE 与 BSM 关键路径稳定性。

## 影响范围
- 前端：`web/components/`, `web/app/analyze/`, `web/i18n/messages/`, `web/tests/`
- 算法 Skill：`skills/algorithms/bsm_pricer/`
- 后端测试：`tests/test_bsm_pricer.py`, `tests/api/test_analyze_stream.py`
- 不触达领地外目录，不改 `src/agents/orchestrator.py`、`src/llm/`、`src/config.py`、`CLAUDE.md`

## 验收目标
1. 分析触发后展示实时 SSE 管道进度，完成后回到结果面板，失败可重试。
2. BSM Skill 纯 Python 实现，返回价格与 Greeks，支持 call/put。
3. 新增前端组件测试、后端 API/Skill 测试并通过既定验证命令。

## Size: L
## 推断依据
- 范围：跨前端组件/页面/i18n、算法 skill、前后端测试，跨模块。
- 关键词：feature + integration + testing，非单点修复。
- 预估文件数：10+（新建与修改并存）。
- 依赖变更：无新增外部依赖，但存在前后端联动与 SSE 协议对齐。
- 风险：分析主流程 UI 交互与事件映射，需完整回归验证。
- 基线：`.devkit/project.yaml` 标记项目 scale 为 `L`，本次任务与基线一致。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP
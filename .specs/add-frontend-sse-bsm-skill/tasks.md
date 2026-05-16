# Tasks: add-frontend-sse-bsm-skill

## 任务波次

### Wave 1（无依赖，可并行）
#### T01: 新增 BSM Skill 实现
- 描述: 新建 `skills/algorithms/bsm_pricer/skill.py`，实现纯 Python `_norm_cdf/_norm_pdf`、BSM 价格与 Greeks、边界 `T=0/σ=0`。
- read_files: [`src/skills/base.py`, `skills/algorithms/volume_profile/skill.py`, `skills/algorithms/gex_calculator/skill.py`]
- write_files: [`skills/algorithms/bsm_pricer/skill.py`]
- verify: `python3 -m py_compile skills/algorithms/bsm_pricer/skill.py`
- status: done

#### T02: 新增 Skill 元数据
- 描述: 新建 `skills/algorithms/bsm_pricer/skill.yaml`，补齐 name/type/entry_point/version。
- read_files: [`skills/algorithms/volume_profile/skill.py` (结构参考)]
- write_files: [`skills/algorithms/bsm_pricer/skill.yaml`]
- verify: `python3 -c "from skills.algorithms.bsm_pricer.skill import BSMPricerSkill; print(BSMPricerSkill().description)"`
- status: done

#### T03: 补齐 AnalysisProgress i18n 类型与消息
- 描述: 在 `web/i18n/types.ts` 扩展 `InteractionMessages`，在 `web/i18n/messages/interaction.ts` 增加进度相关双语 key。
- read_files: [`web/i18n/types.ts`, `web/i18n/messages/interaction.ts`, `web/i18n/get-message.ts`]
- write_files: [`web/i18n/types.ts`, `web/i18n/messages/interaction.ts`]
- verify: `cd web && npx tsc --noEmit`
- status: done

### Wave 2（依赖 Wave 1）
#### T04: 实现 AnalysisProgress 组件
- 描述: 新建 `web/components/AnalysisProgress.tsx`，实现 SSE 事件映射、步骤状态机、耗时展示、自动重连 1 次、手动重试。
- depends_on: [T03]
- read_files: [`web/lib/api.ts`, `web/components/StatusPanel.tsx`, `web/components/AnalyzeForm.tsx`]
- write_files: [`web/components/AnalysisProgress.tsx`]
- verify: `cd web && npx tsc --noEmit`
- status: done

#### T05: 集成 AnalysisProgress 到 AnalyzeForm
- 描述: 修改 `web/components/AnalyzeForm.tsx`，分析运行阶段切到 `AnalysisProgress`，完成后显示现有结果列表，错误态可重试。
- depends_on: [T04]
- read_files: [`web/components/AnalyzeForm.tsx`, `web/lib/api.ts`]
- write_files: [`web/components/AnalyzeForm.tsx`]
- verify: `cd web && npx tsc --noEmit`
- status: done

#### T06: 新增 AnalysisProgress 前端测试
- 描述: 新建 `web/tests/components/analysis-progress.test.ts`，覆盖渲染、事件映射、done 回调、error+retry、双语 key 使用。
- depends_on: [T04, T05]
- read_files: [`web/tests/components/analysis-panel.test.ts`, `web/tests/components/locale-provider.test.ts`]
- write_files: [`web/tests/components/analysis-progress.test.ts`]
- verify: `cd web && npx vitest run tests/components/analysis-progress.test.ts`
- status: done

### Wave 3（依赖 Wave 1）
#### T07: 新增 BSM 数值与边界测试
- 描述: 新建 `tests/test_bsm_pricer.py`，覆盖 ATM/ITM/OTM/Parity/边界/零波动。
- depends_on: [T01, T02]
- read_files: [`src/skills/base.py`, `tests/test_volume_profile.py`]
- write_files: [`tests/test_bsm_pricer.py`]
- verify: `python -m pytest tests/test_bsm_pricer.py -x -v`
- status: done

#### T08: 新增 SSE API 集成测试
- 描述: 新建 `tests/api/test_analyze_stream.py`，覆盖 content-type、事件序列、invalid symbol error、空 symbols 400、no-cache header。
- depends_on: [T05]
- read_files: [`src/api/routes/analyze_stream.py`, `tests/api/test_analyze.py`]
- write_files: [`tests/api/test_analyze_stream.py`]
- verify: `python -m pytest tests/api/test_analyze_stream.py -x -v`
- status: done

### Wave 4（整体验证）
#### T09: 执行验收矩阵并更新验证产物
- 描述: 执行 SPEC 定义验证命令，汇总 AC 证据，准备进入 5-VERIFY。
- depends_on: [T06, T07, T08]
- read_files: [`.specs/add-frontend-sse-bsm-skill/requirements.md`]
- write_files: [`.specs/add-frontend-sse-bsm-skill/verification.md`]
- verify: `python -m pytest tests/test_bsm_pricer.py tests/api/test_analyze_stream.py -x -v && cd web && npx tsc --noEmit && npx vitest run tests/components/analysis-progress.test.ts`
- status: done

## 风险任务
- T04: SSE stage 文本归一化映射与状态机一致性，需额外覆盖大小写/分隔符变体。
- T07: BSM 边界分支（`T=0`, `σ=0`）易出现除零与精度异常，需严格容差断言。
- T08: 流式事件顺序测试需避免脆弱等待逻辑，优先基于 chunk 解析与序列断言。

## 回滚任务
- R01: 回滚 `AnalyzeForm.tsx` 与 `AnalysisProgress.tsx`，恢复原内联进度展示。
- R02: 删除 `skills/algorithms/bsm_pricer/` 与新增测试文件。
- R03: 回退 i18n 新增 key 与 `InteractionMessages` 扩展字段。

## Alternatives Considered
- 把前端与后端测试拆成独立 change：未采用。当前 AC 强绑定同一交付目标，拆分会增加跨 change 协调成本。

## Migration Plan
- 按 Wave 顺序落地；只在 Wave 依赖满足后推进。
- 每完成任务立即执行任务级 verify，避免集中爆雷。

## Observability
- 任务级 verify 命令即观测入口；Wave 4 汇总为 AC 逐条证据。
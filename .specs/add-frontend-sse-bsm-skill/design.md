# Design: add-frontend-sse-bsm-skill

## 技术方案概述
本变更拆成三条实现链：
1. 前端 `AnalysisProgress` 客户端组件：负责消费 `runAnalysisStream()` 事件并驱动步骤状态机。
2. 分析页接入：`AnalyzeForm` 从“内联进度+结果”切分为“进度组件 + 结果展示”，保留原有结果渲染能力。
3. 算法能力：新增 `BSMPricerSkill`，纯 Python 实现标准正态 CDF/PDF 与 BSM+Greeks。

目标是最小侵入：不改后端 SSE 协议，不改 orchestrator，不引入新依赖。

## 组件拆分
- `web/components/AnalysisProgress.tsx`（新增）
  - 输入：`symbols`, `onComplete`, `onError`, `autoStart`
  - 内部状态：`progress`, `steps`, `currentMessage`, `error`, `resultSummary`, `hasRetried`
  - 行为：
    - 挂载且 `autoStart=true` 时启动流
    - `start` 初始化步骤
    - `progress` 更新整体百分比与当前描述
    - `step` 更新阶段状态
    - `result` 记录摘要
    - `done` 结束并触发 `onComplete`
    - `error` 错误态，自动重连 1 次；仍失败则显示重试按钮
- `web/components/AnalyzeForm.tsx`（修改）
  - 负责 symbol 选择与分析启动
  - 在 `running` 时渲染 `AnalysisProgress`，完成后渲染现有结果列表
- `web/i18n/messages/interaction.ts` + `web/i18n/types.ts`（修改）
  - 为进度组件补齐双语 key 与类型

## API 设计
- 复用现有前端 API：`runAnalysisStream(symbols, handlers)`（`web/lib/api.ts`）
- 复用后端 SSE contract：`start/progress/step/result/done/error`（`src/api/routes/analyze_stream.py`）
- 不新增 HTTP endpoint，不修改 payload schema。

## 数据模型
### 前端步骤模型
```ts
type StepStatus = 'pending' | 'running' | 'done' | 'error'

type PipelineStepKey = 'data_harvester' | 'quant_brain' | 'strategy' | 'memory'

interface PipelineStepView {
  key: PipelineStepKey
  label: string
  status: StepStatus
  elapsedMs: number | null
}
```

### BSM 输出模型（SkillResult.data）
```python
{
  "price": float,
  "delta": float,
  "gamma": float,
  "theta": float,  # per day
  "vega": float,   # per 1% IV
  "rho": float,
  "intrinsic_value": float,
  "time_value": float,
  "d1": float,
  "d2": float
}
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| SSE `stage` 文本与步骤 key 不同 | 步骤状态更新错位 | 做字符串归一化映射（lowercase + 分隔符兼容）并保留 fallback |
| 流异常导致 UI 卡死 running | 用户无法继续分析 | 自动重连一次 + 手动重试按钮 + 失败回调 |
| BSM 边界 `T=0/σ=0` 除零 | 计算错误/异常 | 在 execute 内显式分支处理，走贴现内在价值与稳定 Greeks |
| i18n key 未同步类型 | TS 报错或运行时取值失败 | 同步更新 `InteractionMessages` 类型与消息字典 |
| 前端改动影响既有结果展示 | 回归风险 | 保留现有结果结构，仅替换运行阶段展示容器 |

## 回滚计划
- 回滚 `AnalyzeForm.tsx` 到原先内联进度实现。
- 删除 `AnalysisProgress.tsx` 与对应测试。
- 删除 `bsm_pricer` skill 目录和新增后端测试。
- 回滚 i18n 新增字段。

## 架构决策记录（ADR）
### ADR-1: 复用现有 `runAnalysisStream`，不改后端协议
- 状态: accepted
- 上下文: 后端已稳定产出 SSE 事件。
- 决策: 前端组件按既有事件消费，不改 route 与事件格式。
- 后果: 改动集中在 UI 层，后端无联动风险。

### ADR-2: BSM 采用纯 Python 正态函数
- 状态: accepted
- 上下文: 需求明确禁止 scipy 依赖。
- 决策: 使用 `math.erf` 实现 `_norm_cdf`，公式实现 `_norm_pdf`。
- 后果: 零外部依赖，精度可满足测试容差。

### ADR-3: 自动重连仅一次
- 状态: accepted
- 上下文: 需求要求断线自动重试一次，避免无限重连。
- 决策: 组件维护 `hasRetried` 标记，只做 1 次自动重连。
- 后果: 行为可预测，测试覆盖简单。

## Alternatives Considered
- 改为 EventSource 直连后端：未采用。当前 POST + body 语义依赖 fetch stream。
- 在 `AnalyzeForm` 内继续内联步骤 UI：未采用。状态机会继续膨胀，测试成本更高。

## Migration Plan
1. 先新增 `AnalysisProgress` + i18n key + 组件测试。
2. 再接入 `AnalyzeForm`。
3. 并行新增 `bsm_pricer` + skill tests。
4. 最后补 `tests/api/test_analyze_stream.py`，执行验证矩阵。

## Observability
- 前端显示：当前步骤、状态图标、总进度、耗时、错误信息。
- 自动化证据：
  - 组件测试覆盖事件到 UI 状态映射。
  - API 测试覆盖 SSE 事件序列。
  - BSM 测试覆盖核心数值与边界。
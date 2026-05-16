# Requirements: add-frontend-sse-bsm-skill

## 功能需求
### FR-1: SSE 进度组件
- Given: 用户在分析页提交 symbols。
- When: 前端调用 `runAnalysisStream()` 接收 SSE 事件。
- Then: `AnalysisProgress` 实时展示整体进度、四阶段步骤状态、当前步骤描述、耗时。

### FR-2: 事件映射与重试
- Given: 后端发出 `start/progress/step/result/done/error` 事件。
- When: 组件消费事件流。
- Then: 事件映射到 UI 状态机；网络断开后自动重连 1 次；错误态展示重试按钮并可手动重试。

### FR-3: 页面集成
- Given: 分析页初始状态。
- When: 用户点击 Analyze。
- Then: 进入 AnalysisProgress；收到 done 后切回现有 `AnalysisPanel` 结果区；错误时保留错误反馈与重试入口。

### FR-4: 双语文案
- Given: 语言环境 `zh-CN` 或 `en`。
- When: 渲染 AnalysisProgress 文案。
- Then: 所有用户可见文案走 i18n key，双语完整。

### FR-5: BSM 定价 Skill
- Given: 输入 `spot/strike/time_to_expiry/risk_free_rate/volatility/option_type`。
- When: 调用 `BSMPricerSkill.execute()`。
- Then: 返回 `price/delta/gamma/theta/vega/rho/intrinsic_value/time_value/d1/d2`。

### FR-6: Skill 可发现性
- Given: SkillRegistry 扫描算法目录。
- When: 存在 `skills/algorithms/bsm_pricer/skill.py + skill.yaml`。
- Then: 可被注册并实例化。

### FR-7: 测试覆盖
- Given: 新能力已实现。
- When: 执行指定 pytest / vitest / typecheck 命令。
- Then: BSM 数值、SSE 事件序列、前端组件交互与 i18n 路径均有自动化覆盖。

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 分析页显示四阶段实时进度并随 SSE 更新 | `web/tests/components/analysis-progress.test.ts` 覆盖 start/progress/step/done 分支；手动检查 `web/app/analyze/page.tsx` 流程切换 |
| AC-2: 错误态可见且支持自动重连一次+手动重试 | 组件测试覆盖 error 与 retry；断线重连计数断言 |
| AC-3: 进度组件全部文案支持 zh-CN/en | i18n 单测或组件语言切换断言；检查 message key 无硬编码 |
| AC-4: BSM Skill 纯 Python 实现且无 scipy 依赖 | `python3 -m py_compile skills/algorithms/bsm_pricer/skill.py` + grep 依赖 + 导入验证命令 |
| AC-5: ATM/ITM/OTM/Parity/边界/零波动结果满足容差 | `python -m pytest tests/test_bsm_pricer.py -x -v` |
| AC-6: `/api/analyze/stream` 事件序列与错误路径正确 | `python -m pytest tests/api/test_analyze_stream.py -x -v` |
| AC-7: 前端类型与组件测试通过 | `cd web && npx tsc --noEmit`；`cd web && npx vitest run tests/components/analysis-progress.test.ts` |
| AC-8: 新增改动不破坏后端主测试集 | `python -m pytest tests/ -x --tb=short` |

## 用户故事
- As a 量化研究用户, I want 分析过程可视化, So that 我能判断当前卡在哪个阶段与是否可重试。
- As a 策略开发者, I want 可复用 BSM Greeks 结果, So that 我能在期权策略中直接消费理论定价。

## 非功能需求
### NFR-1: 前端可维护性
`AnalysisProgress.tsx` 控制在 300 行以内，状态流清晰可测试。

### NFR-2: 兼容性
不新增第三方 Python 依赖；保持现有 Skill 加载机制不变。

### NFR-3: 稳定性
SSE 网络抖动下至少一次自动重连，避免瞬时断连直接失败。

## 边界场景
### Edge-1: symbols 为空
后端返回 400，前端展示错误态。

### Edge-2: invalid symbol
SSE 返回 error 事件，组件转错误态并保留重试能力。

### Edge-3: T→0 或 σ=0
BSM 需防除零并按边界公式返回可解释结果。

## 回滚计划
- 回滚前端：移除 `AnalysisProgress` 接入，恢复页面原 loading 逻辑。
- 回滚算法：删除 `skills/algorithms/bsm_pricer/` 与对应测试。
- 回滚测试：移除新增测试文件，恢复基线。

## 数据/权限影响
- 无数据库 schema 改动。
- 无权限模型改动。
- 无新增外部服务鉴权。

## Alternatives Considered
- 方案 A：复用现有简单 loading，不做步骤化。未采用，缺乏阶段可观测性与诊断能力。
- 方案 B：BSM 依赖 scipy。未采用，不符合“纯 Python 无额外依赖”约束。

## Migration Plan
- 先补前端组件与 i18n，再做页面接入。
- 并行实现 BSM Skill 与后端测试。
- 最后统一执行前后端验证矩阵。

## Observability
- 组件显示当前步骤、状态、耗时与错误文本。
- SSE 测试验证事件顺序与关键响应头，确保协议层可观测。

## 排除范围（Out of Scope）
- 不改分析后端核心业务编排逻辑。
- 不扩展额外期权模型（如 Binomial、Heston）。
- 不引入新状态管理库。
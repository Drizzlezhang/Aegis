# Change: sprint8-aegis-tracking

## 概述
新增决策追踪（Decision Tracking）模块，在策略分析完成后自动记录推荐，并通过 yfinance 历史数据追踪推荐是否命中止盈/止损/到期，提供命中率统计 API。

## 动机
当前系统分析出推荐后无后续追踪，无法量化策略推荐质量。需引入闭环追踪机制，记录推荐 → 验证 → 统计全链路。

## 影响范围
- **新建** `src/services/tracking/`（models + service）
- **新建** `src/api/routes/tracking.py`（3 个 API 端点）
- **修改** `src/scheduler/engine.py`（集成自动记录 hook + 每日 16:30 更新 cron）
- **修改** `src/api/main.py`（注册 tracking route + app.state）
- **新建** `tests/services/test_tracking/`（6 个测试）
- **禁止修改** `web/`、`src/agents/`、`src/llm/`、`src/backtest/`

## 验收目标
1. TrackedDecision 模型可正常创建，枚举值正确
2. TrackingService 可记录推荐、持久化 JSON、批量更新状态、统计命中率
3. API 端点返回正确的 JSON 响应（stats / decisions list / manual update）
4. Scheduler 在分析完成后自动记录推荐，每日 16:30 自动触发追踪更新
5. 6 个单元测试全部通过
6. 全量回归测试通过（排除 e2e/ 和 vector_store）

## Size: S
## 推断依据
- 范围：跨模块（services + API + scheduler），但都是新增/小幅修改
- 文件数：~9（4 新建源文件 + 2 修改 + 3 测试文件）
- 关键词：`feat`（新功能模块）
- 依赖：仅内部模块 + 已有 yfinance，不引入新外部依赖
- 风险：局部影响，需回归测试但无破坏性变更

## 阶段序列
0 → 1 → 4 → 5 → 6（S 跳过 DESIGN/PLAN）
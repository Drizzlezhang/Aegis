# Requirements: sprint8-aegis-tracking

## 功能需求

### FR-1: TrackedDecision 数据模型
- Given: 策略分析产生了一条推荐
- When: 系统实例化 TrackedDecision
- Then: 决策应包含 id/symbol/strategy_type/recommended_at/entry_price/target_price/stop_loss_price/expiry_date/confidence/status 等字段，status 默认为 PENDING，可选字段（pnl_pct/hit_date）默认为 None

### FR-2: 记录推荐
- Given: 策略分析产生了推荐结果（symbol/strategy_type/entry_price/target_price/stop_loss/confidence）
- When: 调用 TrackingService.record_recommendation(...)
- Then: 生成 TrackedDecision 对象，status=PENDING，持久化到 JSON 文件，返回该 Decision

### FR-3: 批量更新追踪状态
- Given: 存在 PENDING/ACTIVE 状态的追踪决策
- When: 调用 TrackingService.update_all()
- Then: 通过 yfinance 拉取推荐日期以来的历史数据，根据最高价/最低价判断是否触发止盈/止损/到期，更新 status/actual_high/actual_low/pnl_pct/hit_date，持久化结果

### FR-4: 命中率统计
- Given: 存在已完成的追踪决策（非 PENDING/ACTIVE）
- When: 调用 TrackingService.get_stats()
- Then: 返回 total/hit_rate/avg_pnl_pct/by_strategy（分策略命中率）/pending 数量

### FR-5: 最近追踪列表
- Given: 存在多条追踪记录
- When: 调用 TrackingService.list_recent(limit=20)
- Then: 按 recommended_at 降序返回最近 N 条

### FR-6: API 端点
- Given: 服务已启动，tracking_service 已注册到 app.state
- When: 请求 GET /api/tracking/stats, GET /api/tracking/decisions?limit=N, POST /api/tracking/update
- Then: 分别返回统计数据 JSON、决策列表 JSON、更新确认 JSON，所有字段 snake_case

### FR-7: Scheduler 集成
- Given: AnalysisScheduler 正常运行
- When: analyze_one 产生推荐结果后
- Then: 自动调用 record_recommendation 记录追踪
- When: 调度器初始化时
- Then: 注册每日 16:30 的 CronTrigger 自动执行 update_all

### FR-8: main.py 注册
- Given: FastAPI 应用启动
- When: lifespan 执行
- Then: app.state.tracking_service = TrackingService()，tracking router 注册到 /api 前缀

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: TrackedDecision 创建时 status=PENDING, 可选字段为 None | `test_models.py::test_tracked_decision_creation` — 断言 status==PENDING, pnl_pct is None |
| AC-2: TrackingStatus 枚举值正确 | `test_models.py::test_tracking_status_enum` — 断言 str 值匹配 |
| AC-3: record_recommendation 成功创建并持久化 | `test_service.py::test_record_recommendation` — 断言 symbol/status/confidence 正确, list_recent 返回 1 条 |
| AC-4: get_stats 空数据返回零值 | `test_service.py::test_get_stats_empty` — 断言 total==0, hit_rate==0 |
| AC-5: get_stats 正确计算命中率 | `test_service.py::test_get_stats_with_completed` — 断言 total==2, hit_rate==0.5, by_strategy 正确 |
| AC-6: list_recent 按时间降序 | `test_service.py::test_list_recent_ordered` — 断言最新记录排在前面 |
| AC-7: py_compile 三个新文件无语法错误 | `python3 -m py_compile models.py service.py tracking.py` |
| AC-8: 全量回归测试通过 | `pytest tests/ -x --ignore=tests/e2e/ --ignore=tests/agents/test_vector_store.py` |

## 用户故事
- As a 策略开发者, I want 系统在分析完成后自动记录推荐并追踪其表现, So that 我可以量化评估各策略的推荐质量
- As a 系统用户, I want 通过 API 查看追踪统计与命中率, So that 我可以在仪表盘中可视化策略表现

## 排除范围（Out of Scope）
- **前端展示** — 由 aegis-polish 分支负责
- **数据库存储** — 单用户场景，继续使用 JSON 文件
- **实时追踪** — 非实时系统，每日收盘后批量更新
- **自动调参** — 只统计命中率，不根据结果调整策略参数
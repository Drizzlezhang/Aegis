# Change: sprint3-session4-frontend-skills

## 概述
实现 Sprint 3 Session 4：持仓仪表盘、实时告警、Pipeline 健康可视化、对应 API 集成与测试闭环。

## 动机
Sprint 2 已完成分析输入与结果展示，本次补齐持仓全景监控与运行健康可观测性，形成可用交易运营界面。

## 影响范围
- 前端：`web/app/positions/*`、`web/components/*`、`web/i18n/*`、`web/tests/*`
- 后端 API：`src/api/routes/positions.py`、`src/api/routes/status.py`、`src/api/main.py`（若需注册）
- 测试：`tests/api/*`、`tests/test_bsm_pricer.py`（回归）

## 验收目标
- Positions 页面可展示 summary/table/alerts 三块视图并可双语切换。
- `/api/positions/summary`、`/api/positions/{id}/chain`、`/api/positions/alerts` 可用并有测试覆盖。
- PipelineHealth 在前端可展示 6-agent 状态与运行指标。
- Sidebar 增加 Positions 入口。
- 全量验证链路通过（py_compile、pytest、web build、vitest、回归）。

## Size: L
## 推断依据
- 范围：跨前端页面/组件/i18n/API/测试，多模块联动。
- 关键词：dashboard、real-time monitoring、API integration、tests 完整升级。
- 预估文件数：10+（含新增页面、组件、API 路由、测试、i18n 扩展）。
- 风险：涉及实时刷新、状态展示一致性、跨端契约稳定性，需要完整回归。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

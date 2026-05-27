# Proposal: sprint11-aegis-notify

## 一句话目标
抽象通知架构，新增 Webhook 通道，实现按 alert level 路由分发，前端增加通知中心组件和通知配置区域。

## Size: M

## 推断依据
- 范围：跨模块（`src/services/notification/`、`src/api/routes/`、`web/components/`、`web/app/settings/`）
- 关键词：`abstract`、`refactor`、`new channel`、`router`、`component`
- 预估文件数：~10（3 新后端文件 + 1 重构 + 1 API route + 1 前端组件 + 1 页面修改 + 2 测试文件）
- 依赖变更：新增 httpx 依赖（WebhookNotifier），TelegramNotifier 重构需保持向后兼容
- 风险：TelegramNotifier 重构可能影响现有通知链路，需回归验证

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

## 变更边界
- 新增：`src/services/notification/base.py`、`webhook.py`、`router.py`
- 重构：`src/services/notification/telegram.py`（继承 base，保持向后兼容）
- 新增：`src/api/routes/notifications.py`
- 修改：`src/api/main.py`（注册 router + lifespan 初始化）
- 新增：`web/components/NotificationCenter.tsx`
- 修改：`web/app/settings/page.tsx`（新增 Webhook 配置区域）
- 修改：`web/lib/api.ts`（新增 notification API 函数）
- 新增：`tests/services/test_notification/test_webhook.py`
- 新增：`tests/services/test_notification/test_router.py`

## 排除范围
- `src/agents/`（全部）
- `src/scheduler/engine.py`
- `src/llm/`、`src/backtest/`、`src/observability/`
- `src/config.py`
- `src/api/routes/positions.py`、`backtest.py`、`tracking.py`
- `web/app/positions/`、`backtest/`、`tracking/`、`analyze/`
- `web/hooks/`
- `web/components/PositionTable.tsx`、`AnalysisProgress.tsx`、`AlertsPanel.tsx`
- `Dockerfile`、`docker-compose.yml`

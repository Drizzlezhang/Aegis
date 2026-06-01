# Sprint16 Branch E — 端到端验收文档

> 生成日期: 2026-06-01
> 分支: sprint16-branch-E-observability-realtime

## 一、三个不变量实测证据

### 不变量 1: 契约冻结

Branch E 不写新表、不动契约。所有 API 端点复用 Branch A 已定义的 contracts。

- `SignalEvent` (`src/contracts/signal_event.py`) — 未修改
- `DecisionContext` / `FusedSignal` (`src/contracts/decision_context.py`) — 未修改
- `PushEvent` (`src/services/event_bus.py:116`) — 未修改

**验证命令:**
```bash
git diff master -- src/contracts/
# 预期输出: (空)
```

### 不变量 2: no _mock

所有 API 端点已移除 `_mock` 标记，返回基于 fixtures 的非空数据。

**验证命令:**
```bash
grep -rn "_mock" src/ web/app/ web/components/ | grep -v ".specs/" | grep -v "node_modules/" | grep -v "test_" | grep -v "_test."
# 预期输出: (空)
```

### 不变量 3: 宪法一致

L1/L2/L3 守卫全部通过，不包含任何下单相关代码或文案。

**验证命令:**
```bash
bash scripts/constitution_grep.sh
# 预期输出: 退出码 0
```

## 二、API 端点验证

### GET /api/signals

```bash
curl -s http://localhost:8000/api/signals | python3 -m json.tool
```

预期输出: 3 条信号（polymarket / x_social / macro_news），无 `_mock` 字段。

### GET /api/decisions

```bash
curl -s http://localhost:8000/api/decisions | python3 -m json.tool
```

预期输出: 2 条决策（AAPL / TSLA），无 `_mock` 字段。

### GET /api/decisions/{id}/trace

```bash
curl -s http://localhost:8000/api/decisions/test-id/trace | python3 -m json.tool
```

预期输出: 包含 `signal_events`、`fused_signal`、`context_snapshot` 三段数据。

### WS /ws/push

```bash
# 使用 websocat 或 Python websockets 连接
python3 -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('ws://localhost:8000/ws/push') as ws:
        print('Connected to /ws/push')
asyncio.run(test())
"
```

预期输出: Connected to /ws/push

## 三、UI 页面清单

| 页面 | 路由 | 文件 | 状态 |
|------|------|------|------|
| 信号面板 | `/signals` | `web/app/signals/page.tsx` | ✅ 已创建 |
| 决策 Trace | `/decisions/[id]` | `web/app/decisions/[id]/page.tsx` | ✅ 已创建 |
| 推送通知 | 全局组件 | `web/components/PushBanner.tsx` | ✅ 已创建 |
| 侧边栏导航 | — | `web/components/Sidebar.tsx` | ✅ 已更新 |

## 四、E2E Smoke 脚本

```bash
bash scripts/e2e_smoke.sh
```

预期输出: `E2E smoke passed`，退出码 0。

## 五、截图占位

<!-- TODO: 添加 UI 截图 -->
- [ ] 信号面板截图
- [ ] 决策 Trace 截图
- [ ] PushBanner toast 截图

# Design: sprint16-branch-F-fixes-and-polish

<!-- size:all -->
## 技术方案概述
Branch F 是纯修复+打磨分支，不引入新架构概念。8 个修复项按优先级分 4 波执行：CRITICAL 字段对齐 → HIGH 前端补全 → MEDIUM 逻辑修复 → LOW 依赖+Telegram。

## 组件拆分

| 修复 | 模块 | 文件 | 变更类型 |
|------|------|------|---------|
| F-1 | 前端 trace 页 + E2E + 测试 | `decisions/[id]/page.tsx`, `e2e_smoke.sh`, `test_mock_routes.py` | 字段名对齐 |
| F-2 | E2E smoke | `e2e_smoke.sh` | WS 路径修复 |
| F-3a | 前端 layout | `layout.tsx` | 挂载 PushBanner |
| F-3b | 前端 decisions 列表 | `decisions/page.tsx` (新建) | 新页面 |
| F-4 | 测试 | `test_mock_routes.py` | fixture 修复 |
| F-5 | 后端 composer | `decision_composer.py` | 时序修复 |
| F-6 | 前端 signals | `signals/page.tsx` | since 筛选器 |
| F-7 | 后端 X adapter | `x_social/adapter.py` | TODO 标记 |
| F-8a | 依赖 | `pyproject.toml` | 已存在，无需修改 |
| F-8b | 后端 Telegram | `telegram.py` (新建), `main.py` | 真实 adapter |
<!-- /size:all -->

<!-- size:S+ -->
## API 设计

### F-1: trace API 字段名（已是现状，前端对齐）
后端 `GET /api/decisions/{id}/trace` 已返回：
```json
{
  "decision_id": "...",
  "signals": [...],
  "fusion": {...},
  "wyckoff_and_final": {...}
}
```
前端、E2E smoke、test_mock_routes.py 需从旧 key (`signal_events`/`fused_signal`/`context_snapshot`) 对齐到新 key。

### F-6: signals API 新增 since 参数
`GET /api/signals?source=&sentiment=&since=2026-01-01T00:00&limit=50`
后端 `signals.py` 已支持 `since` 参数（Annotated[datetime | None, Query()]），前端只需传递。
<!-- /size:S+ -->

<!-- size:M+ -->
## 数据模型

### F-1: 前端 DecisionTrace 接口更新
```typescript
// 旧（删除）
interface DecisionTrace {
  signal_events: SignalEvent[];
  fused_signal: FusedSignal;
  context_snapshot: {...};
}

// 新
interface DecisionTrace {
  signals: SignalEvent[];
  fusion: FusedSignal;
  wyckoff_and_final: {
    wyckoff_phase?: string;
    action?: string;
    rationale?: string;
    [key: string]: unknown;
  };
}
```

### F-5: DecisionComposer 签名变更
```python
# compose() 新增可选参数 decision_log
async def compose(
    self,
    symbol: str,
    wyckoff_phase: str,
    current_price: float | None,
    watchlist_position: dict,
    signals: list[SignalEvent],
    decision_log: DecisionLog | None = None,  # 新增
) -> DecisionContext:
```

流程变更：
1. 构建 DecisionContext（不变）
2. 若 `decision_log` 非 None，先 `append_with_context` 拿到 `decision_id`
3. 发布 `DecisionGeneratedEvent` 时填入真实 `decision_id`
4. 若 `decision_log` 为 None，保持 `decision_id=""`（向后兼容）

### F-8b: TelegramAdapter
```python
class TelegramAdapter(PushAdapter):
    def __init__(self, bot_token: str, chat_id: str) -> None
    async def send(self, event: PushEvent) -> bool
```
使用 httpx 调用 `https://api.telegram.org/bot{token}/sendMessage`，Markdown 格式，10s 超时，异常返回 False。

### F-8b: main.py lifespan 集成
```python
config = get_config()
if config.telegram.bot_token and config.telegram.chat_id:
    from src.services.push_adapters.telegram import TelegramAdapter
    tg_adapter = TelegramAdapter(config.telegram.bot_token, config.telegram.chat_id)
else:
    from src.services.push_adapters.telegram_stub import TelegramStubAdapter
    tg_adapter = TelegramStubAdapter()
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| F-1 字段名变更是破坏性的 | 前端 trace 页渲染失败 | 前后端同步修改，E2E smoke 验证 |
| F-5 compose 签名变更 | 现有调用方需更新 | decision_log 参数可选（默认 None），向后兼容 |
| F-4 test fixture 修复 | 可能暴露其他测试依赖问题 | 使用 `with TestClient(app)` 触发 lifespan |
| F-8b Telegram API 不可达 | send() 返回 False | 异常捕获 + 日志，不影响主流程 |

## 回滚计划
- 每个 F-x 独立 commit，可单独 revert
- F-1 字段名变更需前后端同步回滚
- F-5 签名变更向后兼容，回滚无影响
<!-- /size:M+ -->

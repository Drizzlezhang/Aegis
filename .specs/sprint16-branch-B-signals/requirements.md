# Requirements: sprint16-branch-B-signals

## 概述
接入 3 个外部信号源（Polymarket、X/Twitter、Macro News），统一通过 Branch A 的 `SignalSource` ABC + `SignalEvent` 契约对外暴露，落库 `signal_events` 表 + 发布 `SignalReceivedEvent` 到 EventBus，替换 mock `/api/signals` 路由为真实查询。

---

## 功能需求

### FR1: Polymarket Adapter
- **描述**: 实现 `PolymarketAdapter(SignalSource)`，从 Polymarket Gamma API 拉取活跃市场数据，按 watchlist symbol 关键词匹配，将 yes 概率映射为 `SignalSentiment`。
- **数据源**: `GET https://gamma-api.polymarket.com/markets?active=true&limit=50`
- **映射规则**:
  - `p > 0.6` → `BULLISH`
  - `p < 0.4` → `BEARISH`
  - 否则 → `NEUTRAL`
- **confidence**: `abs(p - 0.5) * 2`
- **source_id**: `"polymarket"`
- **fetch_interval_seconds**: `300`

### FR2: X (Twitter) Adapter
- **描述**: 实现 `XSocialAdapter(SignalSource)`，通过 Apify/RapidAPI scraper 拉取 KOL 列表最新推文，用关键词规则匹配情绪（无 LLM 调用）。
- **KOL 配置**: `config/x_kols.yaml`（账号 + 关注 symbol）
- **情绪规则**: 关键词匹配（"买入"/"看多"/"sell"/"crash" 等）
- **source_id**: `"x"`
- **fetch_interval_seconds**: `600`

### FR3: Macro News Adapter
- **描述**: 实现 `MacroNewsAdapter(SignalSource)`，从 GDELT 2.0 或 NewsAPI 拉取宏观新闻。
- **symbols**: 留空（宏观信号不绑 ticker）
- **sentiment**: 用 GDELT tone 字段映射（>1 BULLISH, <-1 BEARISH, 否则 NEUTRAL）
- **source_id**: `"macro_news"`
- **fetch_interval_seconds**: `900`

### FR4: Signal Collector
- **描述**: 实现 `SignalCollector`，管理多个 `SignalSource`，各自按 `fetch_interval_seconds` 定时拉取，落库 + 发布事件。
- **落库**: `INSERT INTO signal_events ... ON CONFLICT(id) DO NOTHING`
- **事件**: 每条新 signal 发布 `SignalReceivedEvent` 到 EventBus

### FR5: SignalReceivedEvent
- **描述**: 在 `src/services/event_bus.py` 新增 `SignalReceivedEvent(BaseEvent)` dataclass。
- **字段**: `signal: SignalEvent | None = None`

### FR6: 替换 mock /api/signals
- **描述**: 修改 `src/api/routes/signals.py`，把 mock 实现换成真实 `signal_events` 表查询。
- **查询参数**: `source`, `sentiment`, `since`, `limit`
- **响应格式**: `{"items": [...], "total": N, "has_more": bool}`
- **必须移除**: `_mock` 字段

### FR7: health_check
- **描述**: 每个 adapter 必须实现 `health_check()` 方法，返回 `bool`。

---

## 非功能需求

### NFR1: 外部 API 容错
- adapter 调用外部 API 失败时不抛异常，返回空 list，记录 warning 日志

### NFR2: 测试覆盖
- 3 个 adapter 各自有独立单测文件
- 1 个集成测试覆盖完整 pipeline（adapter → collector → DB → EventBus → API）

### NFR3: 宪法合规
- `scripts/constitution_grep.sh` 必须通过（不引入自动下单相关代码）

### NFR4: 无 _mock 残留
- `/api/signals` 响应中不得出现 `_mock` 字段

---

## 验收标准

### AC1: PolymarketAdapter 概率映射边界
- **Given**: Polymarket API 返回 market 数据（yes 概率分别为 0.3, 0.5, 0.7）
- **When**: `PolymarketAdapter.fetch_latest()` 被调用
- **Then**: 返回 3 个 `SignalEvent`，sentiment 分别为 BEARISH / NEUTRAL / BULLISH，confidence 分别为 0.4 / 0.0 / 0.4
- **验证方式**: `tests/signals/test_polymarket_adapter.py` 用 `respx` mock HTTP，断言概率映射边界

### AC2: XSocialAdapter 关键词命中
- **Given**: scraper 返回包含关键词"买入"和"crash"的推文
- **When**: `XSocialAdapter.fetch_latest()` 被调用
- **Then**: 返回对应 sentiment 的 `SignalEvent`
- **验证方式**: `tests/signals/test_x_adapter.py` 用 fixture 喂假 tweet，断言关键词命中

### AC3: MacroNewsAdapter tone 映射
- **Given**: GDELT 返回 tone 值分别为 2.0, 0.5, -1.5 的文章
- **When**: `MacroNewsAdapter.fetch_latest()` 被调用
- **Then**: sentiment 分别为 BULLISH / NEUTRAL / BEARISH
- **验证方式**: `tests/signals/test_macro_news_adapter.py` mock HTTP，断言 tone 映射

### AC4: SignalCollector 落库 + 事件发布
- **Given**: 3 个 adapter 各返回 1 条 fake event
- **When**: SignalCollector 跑一轮
- **Then**: `signal_events` 表有 3 条记录，EventBus 收到 3 个 `SignalReceivedEvent`
- **验证方式**: `tests/integration/test_signal_pipeline.py` 集成测试

### AC5: /api/signals 返回真实数据
- **Given**: `signal_events` 表有数据
- **When**: `GET /api/signals` 被调用
- **Then**: 返回 `{"items": [...], "total": N, "has_more": bool}`，响应中无 `_mock` 字段
- **验证方式**: 集成测试中调 API 断言 + `curl` 手动验证

### AC6: health_check 全部实现
- **Given**: 3 个 adapter 实例
- **When**: 调用 `health_check()`
- **Then**: 每个都返回 `bool`（不抛异常）
- **验证方式**: 各 adapter 单测中包含 `test_health_check` 用例

### AC7: 宪法 grep 通过
- **Given**: Branch B 全部代码已提交
- **When**: `bash scripts/constitution_grep.sh`
- **Then**: exit 0
- **验证方式**: CI 或手动执行

### AC8: 全量测试通过
- **Given**: Branch B 全部代码已提交
- **When**: `pytest tests/signals tests/integration/test_signal_pipeline.py -q`
- **Then**: 全部通过
- **验证方式**: CI 或手动执行

---

## 边界场景

1. **外部 API 超时/不可用**: adapter 返回空 list，不抛异常，记录 warning
2. **Polymarket API 返回空 markets**: 返回空 list
3. **X scraper API 返回空推文**: 返回空 list
4. **GDELT tone 字段缺失**: 默认 NEUTRAL
5. **signal_events 主键冲突**: `ON CONFLICT DO NOTHING`，不报错
6. **SignalCollector 多 source 并发**: 各自独立调度，互不影响
7. **KOL 配置文件不存在**: adapter 初始化时抛明确错误
8. **/api/signals 无数据**: 返回 `{"items": [], "total": 0, "has_more": false}`（无 `_mock`）

---

## Out of Scope

- LLM 情绪分析（留给 C 分支融合层）
- 信号去重逻辑（D 分支 push_dedup 表已建，逻辑由 D 实现）
- 前端信号展示页面（E 分支）
- 实时 WebSocket 推送信号（D 分支）
- Polymarket 以外的预测市场
- X 以外社交媒体（Reddit、Discord 等）
- KOL 列表自动发现/管理

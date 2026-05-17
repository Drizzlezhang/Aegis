# Design: sprint4-s3-memory-decoupled

## 技术方案概述
本 Sprint 在现有 `src/services/` 和 `src/agents/` 基础上新增 5 个独立模块，增强 2 个现有模块。所有新增模块均为纯计算/只读服务，不引入新的外部依赖，不修改 orchestrator 流程。

## 组件拆分

```
src/services/
├── decision_log.py        ← [修改] 新增 quality_score 列 + 批量查询方法
├── decision_scorer.py     ← [新建] 决策质量评分（纯计算）
├── backtest_validator.py  ← [新建] 策略回测验证（纯计算）
├── stats_service.py       ← [新建] 统计数据聚合（只读）
└── __init__.py            ← [修改] 导出新模块

src/agents/
├── aegis_memory/
│   └── agent.py           ← [修改] 新增 find_similar_decisions()
└── position_monitor/
    ├── rules_engine.py    ← [新建] 持仓规则引擎
    └── __init__.py        ← [修改] 导出 RulesEngine
```

### 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `DecisionScorer` | 四维度评分历史决策 | 无外部依赖，纯数值计算 |
| `PositionRulesEngine` | 5 条预置规则评估持仓 | 无外部依赖 |
| `BacktestValidator` | 历史价格回测 + 聚合统计 | 无外部依赖 |
| `StatsService` | 聚合交易统计（只读） | DecisionLog, PositionService |
| `find_similar_decisions` | 向量检索相似历史决策 | VectorStore (已有) |
| `DecisionLog` 增强 | quality_score 读写 + 批量查询 | SQLite (已有) |

## API 设计

### DecisionScorer
```python
class DecisionScorer:
    def score(self, decision: dict, position_history: dict) -> DecisionScore
    # decision: {"id", "symbol", "entry_price", "target_pct", "stop_loss_pct", "strategy_type"}
    # position_history: {"prices_after_entry": list[float], "exit_price": float|None,
    #                    "exit_reason": str, "position_size_pct": float, "days_held": int,
    #                    "plan_adherence": str, "was_profitable": bool}
```

### PositionRulesEngine
```python
class PositionRulesEngine:
    def __init__(self, config: dict | None = None)
    def evaluate(self, position: dict, market_data: dict) -> list[RuleResult]
```

### BacktestValidator
```python
class BacktestValidator:
    def validate_strategy(self, symbol, strategy_type, entry_date, entry_price,
                          target_pct, stop_loss_pct, max_days=90,
                          historical_prices=None) -> BacktestResult
    def batch_validate(self, decisions: list[dict]) -> list[BacktestResult]
    def aggregate_stats(self, results: list[BacktestResult]) -> dict
```

### StatsService
```python
class StatsService:
    def __init__(self, decision_log, position_service)
    async def get_trading_stats(self, days: int = 90) -> TradingStats
    async def get_decision_quality_distribution(self) -> dict[str, int]
    async def get_strategy_performance(self) -> list[dict]
```

### AegisMemory 新增方法
```python
async def find_similar_decisions(self, state: AgentState) -> list[dict]
# 通过 self._vector_store.search() 检索，结果写入 state.metadata["similar_decisions"]
```

### DecisionLog 新增方法
```python
async def update_quality_score(self, decision_id: str, score: float, tags: list[str]) -> None
async def get_scored(self, limit: int = 100) -> list[dict]
async def get_recent(self, days: int = 90) -> list[dict]
async def query_by_symbol(self, symbol: str, limit: int = 20) -> list[dict]  # 增强已有方法
```

## 数据模型

### DecisionLog Schema 变更
```sql
-- 新增列（ALTER TABLE ADD COLUMN，可空，兼容现有数据）
ALTER TABLE decisions ADD COLUMN quality_score REAL;
ALTER TABLE decisions ADD COLUMN quality_tags TEXT;
```

完整 schema 变更后：
```sql
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    outcome TEXT NOT NULL,
    actual_pnl REAL,
    reflection TEXT,
    quality_score REAL,        -- [新增] 决策质量评分 0-100
    quality_tags TEXT           -- [新增] JSON 数组，如 '["perfect_timing","perfect_exit"]'
);
```

### 新增 Dataclass
```python
@dataclass
class DecisionScore:
    decision_id: str; symbol: str; total_score: float
    timing_score: float; sizing_score: float; exit_score: float
    plan_adherence: float; tags: list[str]

@dataclass
class RuleResult:
    rule_name: str; action: RuleAction; reason: str
    urgency: int; metadata: dict

@dataclass
class BacktestResult:
    symbol: str; strategy_type: str; entry_date: date; entry_price: float
    exit_date: date | None; exit_price: float | None
    max_gain_pct: float; max_drawdown_pct: float; final_pnl_pct: float | None
    days_held: int; hit_profit_target: bool; hit_stop_loss: bool
    risk_reward_actual: float | None

@dataclass
class TradingStats:
    total_decisions: int; total_positions: int; win_rate: float
    avg_pnl_pct: float; total_realized_pnl: float
    best_trade: dict | None; worst_trade: dict | None
    avg_holding_days: float; monthly_pnl: dict[str, float]
    by_strategy: dict; by_symbol: dict
```

### 数据流
```
DecisionScorer.score()
  └─ decision (dict) + position_history (dict) → DecisionScore

PositionRulesEngine.evaluate()
  └─ position (dict) + market_data (dict) → list[RuleResult]

BacktestValidator.validate_strategy()
  └─ 策略参数 + historical_prices → BacktestResult

AegisMemory.find_similar_decisions()
  └─ AgentState → VectorStore.search() → state.metadata["similar_decisions"]

StatsService.get_trading_stats()
  └─ DecisionLog.get_recent() + PositionService.get_closed_positions() → TradingStats
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| DecisionLog schema 迁移破坏现有数据 | 现有查询/写入失败 | ALTER TABLE ADD COLUMN（可空），不修改现有列；迁移前检查列是否存在 |
| `query_by_symbol` 方法签名冲突 | 已有同名方法返回 `list[DecisionEntry]`，新增需返回 `list[dict]` | 新增方法使用不同名称或参数区分；实际源文档中已有 `query_by_symbol` 返回 DecisionEntry，新增的返回 dict 需重命名或统一 |
| VectorStore 未初始化时 find_similar_decisions 调用失败 | 相似决策检索静默失败 | 已有 None 检查模式，返回空列表 |
| StatsService 依赖的 PositionService 接口不匹配 | get_closed_positions/get_scored 方法不存在 | BUILD 阶段先检查 PositionService 实际接口，必要时适配 |

## 回滚计划
1. 删除新建文件：`decision_scorer.py`、`backtest_validator.py`、`stats_service.py`、`rules_engine.py`
2. 回退 `__init__.py` 的导出变更
3. 回退 `agent.py` 中 `find_similar_decisions` 方法和调用点
4. DecisionLog 新增列保留（可空不影响），或执行 `ALTER TABLE decisions DROP COLUMN quality_score; DROP COLUMN quality_tags;`
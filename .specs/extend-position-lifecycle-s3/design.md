# Design: extend-position-lifecycle-s3

## 技术方案概述
在 Sprint 2 的 DecisionLog、PositionBridge、ReflectionEngine、PositionMonitor 基础上，补全 Position 全生命周期管理（Roll/Close/Expire），建立 Reflection→Memory 反馈闭环，并提供 PositionService 供前端仪表盘查询。

## 组件拆分
| 组件 | 职责 | 修改方式 |
|------|------|---------|
| `src/models/position.py` | 新增 `parent_position_id`、`close_date`、`close_price` | 字段扩展 |
| `src/agents/position_monitor/position_manager.py` | Roll/Close/Expire/查询 | 新增方法 |
| `src/agents/position_monitor/monitor.py` | scan 时自动检测过期 | 新增分支 |
| `src/agents/position_monitor/agent.py` | reflection feedback 收集 | 新增方法 |
| `src/services/decision_log.py` | `query_recent_reflected` | 新增方法 |
| `src/agents/aegis_memory/agent.py` | 存储 reflection 到 vector store | 新增方法 |
| `src/services/position_service.py` | summary + chain API | 新建文件 |
| `src/services/__init__.py` | 导出 PositionService | 追加 |

## API 设计

### PositionManager 新增方法
```python
async def roll_position(self, position_id: str, new_contract: OptionContract, new_entry_price: float) -> Position
async def close_position(self, position_id: str, close_price: float, reason: str = "") -> Position
async def expire_position(self, position_id: str) -> Position
async def get_all_positions(self) -> list[Position]
async def get_position(self, position_id: str) -> Position | None
async def get_position_history(self, symbol: str) -> list[Position]
```

### DecisionLog 新增方法
```python
async def query_recent_reflected(self, limit: int = 5) -> list[DecisionEntry]
```

### PositionService
```python
class PositionService:
    async def get_summary(self) -> PositionSummary
    async def get_position_chain(self, position_id: str) -> list[dict]
```

## 数据模型
```python
class Position(BaseModel):
    # existing fields...
    parent_position_id: str | None = None
    close_date: date | None = None
    close_price: float | None = None
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 旧 Position JSON 反序列化失败 | 高 | 新字段全部 Optional 带默认值 |
| VectorStore 不可用中断主流程 | 中 | `_store_reflection` 用 try/except |
| Roll 操作非原子性 | 中 | 旧仓+新仓变更后统一 `save()` |
| Monitor auto-expire 误触发 | 低 | 仅 `expiry <= date.today()` 时触发 |

## 回滚计划
- 删除 `position_service.py` 与测试文件
- 回退各文件的增量方法
- 移除 Position 模型新字段

# Design: sprint12-branch-d-tests

## 测试架构

### 文件结构
```
tests/
├── conftest.py                          # [追加] 6 个 mock OHLCV fixtures
├── agents/
│   └── test_phase_predictor.py          # [新增] 29 个单元测试
└── integration/
    └── test_phase_predictor_pipeline.py # [新增] 3 个集成测试
```

### 测试分层

#### Layer 1: Fixtures (conftest.py)
- 6 个 mock OHLCV fixtures，覆盖不同市场场景
- 所有 fixtures 返回 `list[OHLCV]`，可直接注入测试方法
- 不依赖外部数据源

#### Layer 2: 单元测试 (test_phase_predictor.py)
按功能分组:
1. **基础运行** (3 tests): 返回类型、7 维验证、权重和
2. **维度评分** (9 tests): 每个维度独立验证
3. **Phase 判定** (6 tests): 6 种 Wyckoff phase 全覆盖
4. **低波动过滤** (2 tests): 触发/不触发
5. **Config 覆盖** (3 tests): 权重/阈值/disabled
6. **数据不足** (2 tests): 短数据/空数据
7. **边界值** (1 test): score clipping

#### Layer 3: 集成测试 (test_phase_predictor_pipeline.py)
- PhasePredictor 在 AgentState pipeline 中的端到端验证
- 报告追加逻辑验证
- MacroRegime 集成验证

### 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Async 测试方式 | `asyncio.run()` | 无需额外依赖 pytest-asyncio |
| Mock 策略 | 不 mock PhasePredictor 内部 | 测试真实逻辑，只 mock 外部依赖 |
| Fixture 位置 | `tests/conftest.py` | pytest 自动发现，跨文件复用 |
| 测试类组织 | `class TestPhasePredictor` | 与现有测试风格一致 |
| 断言风格 | 直接 assert | 简洁，pytest 自带良好错误信息 |

### 依赖关系
```
conftest.py (fixtures)
    ↓
test_phase_predictor.py (单元测试)
    ↓
test_phase_predictor_pipeline.py (集成测试)
```

### 不涉及
- 不修改任何 `src/` 下的生产代码
- 不添加新的 Python 依赖
- 不修改 pytest 配置

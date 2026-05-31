# Change: sprint15-hotfix-v0.15.1.1

## 概述
闭合 v0.15.1 review 中暴露的 3 个必修缺陷：Paper API auth dev-mode 后门（D1）、价格簿死代码（D2）、集成测试 flaky（D3）。

## 动机
v0.15.1 review 给出 Conditional PASS，3 项缺陷阻断 GA：
- D1 (P0): 未配置 token 时全开放，PRODUCTION 下无保护
- D2 (P1): `_get_simulated_price` 从不读 price_cache，价格簿是死代码
- D3 (P0-2 衍生): 硬断言 `status == "filled"` 与 30% 部分成交概率冲突

## 影响范围
- `src/api/auth.py` — profile gate 逻辑
- `src/api/main.py` — lifespan 启动 WARN
- `src/agents/strategy_exec/brokers/paper.py` — 价格簿接入
- `tests/api/test_paper_auth.py` — 替换 dev-mode 测试
- `tests/integration/test_event_bus_lifecycle.py` — flaky 修复
- `tests/brokers/test_paper_price_book.py` — 新增 5 用例
- `tests/conftest.py` — deterministic_full_fill fixture

## 验收目标
7 条验收门全绿（见 plan prompt §4）

## Size: S
## 推断依据
- 范围：3 个聚焦缺陷修复，~5-8 文件
- 关键词：fix（缺陷修复，非新功能）
- 预估文件数：5-8
- 依赖变更：无新增外部依赖
- 风险：局部影响，需回归测试

## 阶段序列
0 → 1 → 4 → 5 → 6（S 跳过 DESIGN/PLAN）

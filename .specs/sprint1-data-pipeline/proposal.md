# Change: sprint1-data-pipeline

## 概述
Sprint 1 Session 1 — 数据采集层重构：BaseFetcher ABC + DataFetcherManager 多源容错 + YFinanceFetcher 实现 + LLM 路由扩展 + Config 扩展 + DataHarvesterAgent 适配 + 测试

## 动机
- 当前 DataHarvesterAgent 基于 SkillRegistry 优先级加载，缺少熔断器、缓存、标准化列等容错机制
- LLM 路由缺少 DEBATE/POSITION 任务类型，后续辩论/持仓模块无法路由
- Config 缺少 DebateConfig/PositionConfig，后续模块无配置入口
- 数据获取层需解耦为 BaseFetcher 抽象 + Manager 容错 + 具体 Fetcher 实现

## 影响范围
- `src/agents/data_harvester/`（核心改动：新增 base_fetcher.py、fetcher_manager.py、fetchers/yfinance_fetcher.py，修改 agent.py）
- `src/llm/router.py`（新增 5 个 TaskType + 路由配置）
- `src/config.py`（新增 DebateConfig、PositionConfig）
- `tests/agents/`（新增 test_base_fetcher.py、test_fetcher_manager.py，修改 test_data_harvester.py）

## 验收目标
1. BaseFetcher ABC 可被子类继承，标准化列映射正确
2. DataFetcherManager 优先级降级、熔断器（3次失败→DOWN→30s半开）、指数退避、LRU缓存均工作
3. YFinanceFetcher 封装现有 yfinance skill 逻辑，priority=10
4. TaskType 新增 DEBATE_QUICK/DEEP/SYNTHESIS、POSITION_MONITOR/REFLECT，路由配置正确
5. DebateConfig + PositionConfig 可通过 get_config() 访问
6. DataHarvesterAgent 使用 DataFetcherManager，保留 SkillRegistry fallback
7. 所有测试通过，全量 pytest 无回归
8. 不修改领地外文件，共享文件只追加

## Size: M
## 推断依据
- 范围：跨 3 个模块（data_harvester、llm、config），但都在 aegis-data 领地内
- 预估文件数：~10（4 新建 + 3 修改 + 3 测试）
- 关键词：feature（新功能开发）
- 依赖变更：仅内部，无新外部依赖
- 风险：需回归测试确保不破坏现有功能

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

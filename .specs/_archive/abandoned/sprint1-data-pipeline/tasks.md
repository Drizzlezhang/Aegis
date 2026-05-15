# Tasks: sprint1-data-pipeline

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: BaseFetcher 抽象基类
- 描述: 新建 BaseFetcher ABC + STANDARD_COLUMNS + FetcherStatus + FetcherHealth + standardize_columns
- read_files: [`src/agents/data_harvester/agent.py`]
- write_files: [`src/agents/data_harvester/base_fetcher.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/base_fetcher.py && python3 -c "from src.agents.data_harvester.base_fetcher import BaseFetcher, STANDARD_COLUMNS, FetcherStatus; print('OK')"`
- status: done

#### T02: LLM 路由扩展
- 描述: TaskType 新增 DEBATE_QUICK/DEEP/SYNTHESIS + POSITION_MONITOR/REFLECT；DEFAULT_ROUTING 新增 5 条映射
- read_files: [`src/llm/router.py`]
- write_files: [`src/llm/router.py`]
- verify: `python3 -c "from src.llm.router import TaskType; assert hasattr(TaskType, 'DEBATE_QUICK'); assert hasattr(TaskType, 'POSITION_MONITOR'); print('OK')"`
- status: done

#### T03: Config 扩展
- 描述: 新增 DebateConfig + PositionConfig，在 Config 类中注册
- read_files: [`src/config.py`]
- write_files: [`src/config.py`]
- verify: `python3 -c "from src.config import get_config; c = get_config(); assert c.debate.max_rounds == 1; assert c.position.max_positions == 10; print('OK')"`
- status: done

### Wave 2（依赖 Wave 1）

#### T04: DataFetcherManager
- 描述: 实现多源容错管理器（优先级降级 + 熔断器 + 指数退避 + LRU缓存）
- depends_on: [T01]
- read_files: [`src/agents/data_harvester/base_fetcher.py`, `src/config.py`]
- write_files: [`src/agents/data_harvester/fetcher_manager.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/fetcher_manager.py && python3 -c "from src.agents.data_harvester.fetcher_manager import DataFetcherManager; print('OK')"`
- status: done

#### T05: YFinanceFetcher 实现
- 描述: 封装 yfinance skill 为 BaseFetcher 子类，priority=10
- depends_on: [T01]
- read_files: [`src/agents/data_harvester/base_fetcher.py`, `skills/data_sources/yfinance_skill/skill.py`]
- write_files: [`src/agents/data_harvester/fetchers/yfinance_fetcher.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/fetchers/yfinance_fetcher.py && python3 -c "from src.agents.data_harvester.fetchers.yfinance_fetcher import YFinanceFetcher; print('OK')"`
- status: done

### Wave 3（依赖 Wave 2）

#### T06: DataHarvesterAgent 适配
- 描述: agent.py 使用 DataFetcherManager，保留 SkillRegistry fallback
- depends_on: [T04, T05]
- read_files: [`src/agents/data_harvester/agent.py`, `src/agents/data_harvester/fetcher_manager.py`]
- write_files: [`src/agents/data_harvester/agent.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/agent.py`
- status: done

#### T07: 编写测试
- 描述: 新建 test_base_fetcher.py + test_fetcher_manager.py，修改 test_data_harvester.py
- depends_on: [T04, T05, T06]
- read_files: [`src/agents/data_harvester/base_fetcher.py`, `src/agents/data_harvester/fetcher_manager.py`, `tests/agents/test_data_harvester.py`]
- write_files: [`tests/agents/test_base_fetcher.py`, `tests/agents/test_fetcher_manager.py`, `tests/agents/test_data_harvester.py`]
- verify: `python -m pytest tests/agents/test_base_fetcher.py tests/agents/test_fetcher_manager.py -x -v`
- status: done

### Wave 4（最终验证）

#### T08: 全量回归验证
- 描述: 全量 pytest + 编译检查 + 导入验证
- depends_on: [T07]
- read_files: []
- write_files: []
- verify: `python -m pytest tests/ -x --tb=short`
- status: done

## 风险任务
- T04（DataFetcherManager）：熔断器/退避逻辑复杂，需仔细测试状态转换
- T06（DataHarvesterAgent）：双路径（Manager + SkillRegistry fallback）需确保 fallback 触发条件清晰

## 回滚任务
- 所有新文件可独立删除回滚
- agent.py 保留原方法作为 fallback
- router.py/config.py 追加部分可单独删除

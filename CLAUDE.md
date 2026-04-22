# Aegis-Trader 项目契约

## 项目定位
专注美股正股及期权（LEAPS, Bull Spreads, Covered Call）的左侧抄底策略的 Multi-Agent 量化交易系统。受 TauricResearch/TradingAgents 启发，但聚焦于**抄底+期权策略**这一垂直场景，引入机构级量化算法和动态 Skill 加载机制。

## 核心标的
- **ETF**: QQQ, SPY
- **科技股**: NVDA, MSFT, AAPL, PLTR, NFLX, INTC, TSM, TSLA
- **防御股**: KO

## 策略方向
- **左侧抄底**: 在支撑位附近建立仓位
- **期权策略**: 10个月+ LEAPS Call, Bull Spreads, Covered Calls
- **多维度支撑计算**: Volume Profile, GEX Wall, 用户先验点位
- **机构级估值**: PE-Band, 多因子模型, 机构共识分析

## 架构核心
- **Multi-Agent 系统**: Data-Harvester, Institutional-Analyst, Strategy-Execution, Aegis-Memory
- **Skill 动态加载**: 参考 Hermes Agent skills/plugins 架构，数据源和算法模块化
- **交易记忆系统**: 参考 Hermes memory plugin 体系，SQLite + 向量存储
- **模型路由**: deepseek-v3.2 (推理), gemini-pro (长文本), minimax-2.7 (快速交互), glm5.1 (代码)

## 目录结构规范
```
TradeAgent/
├── CLAUDE.md                    # 项目契约
├── pyproject.toml               # Python 项目配置
├── .env.example                 # 环境变量模板
├── src/                         # 核心源码
│   ├── skills/                  # Skill 基类与加载器
│   ├── agents/                  # Agent 实现
│   ├── llm/                     # 模型路由
│   └── utils/                   # 工具函数
├── skills/                      # 外部 Skill 模块
│   ├── data_sources/           # 数据源 Skill
│   └── algorithms/             # 算法 Skill
├── web/                         # Next.js 前端仪表盘
├── tests/                       # 测试
└── deploy/                      # 部署配置
```

## 开发规范
### Skill 接口
- 每个 Skill 必须包含 `skill.yaml` 元数据和 `skill.py` 实现
- Skill 基类定义在 `src/skills/base.py`
- 通过 `SkillRegistry` 动态发现和加载

### 环境变量管理
- 所有配置通过环境变量加载
- `.env.example` 提供模板
- 敏感信息（API Keys）必须通过环境变量传递

### 日志追踪
- 结构化日志（JSON 格式）
- 日志级别: DEBUG, INFO, WARNING, ERROR
- Agent 执行链追踪

### 测试要求
- Skill 单元测试覆盖核心功能
- Agent 集成测试验证协作流
- 算法测试验证计算准确性

## 部署架构
- **本地开发**: macOS (Python 3.14, Node.js 25.6.1)
- **GitHub**: private 仓库 Drizzlezhang/Aegis-Trader
- **生产环境**: AWS Singapore (Ubuntu 24.04, 2GB 内存)
- **容器化**: Docker + docker-compose
- **进程管理**: pm2 (Node.js 服务)

## 模型路由策略
通过 NewAPI 统一入口，按任务类型路由：
- **推理/复杂量化**: deepseek-v3.2
- **长文本处理**: gemini-pro
- **快速交互**: minimax-2.7
- **代码生成**: glm5.1

## 风险控制
1. **AWS 内存约束**: 使用 SQLite 替代 PostgreSQL，避免内存密集型缓存
2. **数据源稳定性**: yfinance 为主，alpha_vantage 为备用，后续接长桥/富途
3. **GEX 精度**: yfinance 不提供精确 gamma 和 OI，初期用近似算法
4. **YouTube 抓取**: Phase 2 实现，注意反爬限制

## 验证要求
完成实现后必须验证：
1. Skill 加载器: 动态发现和加载测试
2. yfinance Skill: 获取 QQQ OHLCV 数据非空
3. Volume Profile: POC/VAH/VAL 计算正确性
4. GEX: GEX Wall 识别准确性
5. 端到端: 完整分析报告输出
6. 部署: Docker 容器在 AWS SG 成功启动

## 提交规范
- 每次提交必须有明确的变更摘要
- 关键功能必须附带测试
- 配置变更必须更新 .env.example
- 依赖变更必须更新 pyproject.toml

## 分支策略
- `main`: 稳定版本
- `develop`: 开发分支
- `feature/*`: 功能分支
- `fix/*`: 修复分支

---
*最后更新: 2026-04-22*
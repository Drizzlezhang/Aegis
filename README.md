# Aegis-Trader

**交易决策辅助系统** — 基于 Multi-Agent 架构的美股 Wyckoff 阶段分析与决策辅助工具。

> ⚠️ 本系统是**决策辅助工具**，永不自动下单。所有建议仅供参考，真实交易由用户在券商 App 手动完成。

## 核心能力

- **Wyckoff 阶段识别**：基于量价数据自动判断当前阶段
- **多信号融合**：整合 Polymarket / X / 宏观新闻等多源信号
- **决策建议**：综合阶段 + 信号 + 虚拟持仓给出观察/操作建议
- **回测引擎**：历史数据回放验证策略表现

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 启动后端
python -m src.api.main

# 启动前端
cd web && npm run dev
```

## 技术栈

- **后端**：Python 3.12 / FastAPI / SQLite / Alembic
- **前端**：Next.js / React / TypeScript
- **AI**：LLM 驱动的 Multi-Agent 系统

## 文档

- [系统定位与宪法](docs/system-positioning.md)
- [用户指南](docs/USER_GUIDE.md)

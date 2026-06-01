# Aegis — 私有部署回测决策助手

## 项目定位

Aegis 是单用户私有部署的美股回测决策助手，专注左侧抄底策略分析。不是多租户 SaaS，不是模拟券商交易系统。

- **核心能力**：OHLCV 数据采集 → 多维支撑分析 → Phase 判定 → 策略信号生成 → 回测验证
- **核心标的**：QQQ、SPY、NVDA、MSFT、AAPL、KO、PLTR、NFLX、INTC、TSM、TSLA
- **部署形态**：单机 Docker 或裸机，API 无需鉴权（私有网络内）

## 凭据与配置管理

所有凭据通过项目根目录 `.env` 文件管理，不硬编码、不提交到 Git。

1. 复制 `.env.example` → `.env`
2. 填入必填项（LLM API）
3. 按需填入可选数据源 Key

### 数据源表

| 用途 | 环境变量 | 必填 | 申请地址 |
|------|---------|------|---------|
| LLM 推理 | `AEGIS_LLM_BASE_URL` + `AEGIS_LLM_API_KEY` | 是 | OpenAI / 任意兼容厂商 |
| Alpha Vantage 基本面 | `ALPHA_VANTAGE_API_KEY` | 否 | https://www.alphavantage.co/support/#api-key |
| Reddit 情绪 | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | 否 | https://www.reddit.com/prefs/apps |

## 启动指南

```bash
# 1. 配置凭据
cp .env.example .env
# 编辑 .env，填入 AEGIS_LLM_BASE_URL 和 AEGIS_LLM_API_KEY

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 启动后端
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 4. 启动前端（另一个终端）
cd web && npm install && npm run dev

# 5. 访问 http://localhost:3000/phase
```

## 私有部署声明

- 本系统设计为单用户私有部署，API 完全开放，不设登录鉴权
- 如需暴露公网，请前置 nginx + IP 白名单或 HTTP Basic Auth
- 不提供多租户、RBAC、OAuth 等企业级鉴权能力

## Sprint16 待办

- [ ] 真实券商账户只读同步（持仓、订单、余额）
- [ ] position_monitor 对账 BacktestStore 完善（当前 stub）
- [ ] walk-forward 回测
- [ ] 多策略组合回测

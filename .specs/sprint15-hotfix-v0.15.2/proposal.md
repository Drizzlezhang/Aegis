# Change: sprint15-hotfix-v0.15.2

## 概述
Scope 重对齐 — 把 Aegis 从"模拟券商交易系统 + 多 LLM Provider + 多租户鉴权"瘦身回**单用户私有部署的回测决策助手**。

## 动机
v0.15.1.1 自测后用户提出 5 项 scope 修正，本质是"现实使用场景与代码假设不匹配"：

| # | 用户决策 | 当前代码不匹配点 |
|---|---------|-----------------|
| F1 | 凭据走 `.env` + gitignore + agent.md 记录 | 配置散落在代码默认值 / 环境变量，无统一入口 |
| F2 | LLM 统一走 New API（单 provider） | `LLMProvider` 抽象 + 多家 provider 适配 + router 路由，过度设计 |
| F3 | 私有部署，不要登录 / JWT | 全套登录链路（auth middleware / login page / JWT） |
| F4 | 不要模拟交易，只保留回测 | PaperBroker 模拟撮合，与"回测决策助手"定位反向 |
| F5 | 侧边栏补齐三个缺失入口 | 页面已实现但侧边栏无入口 |

## 影响范围
- **LLM 层**：`src/llm/client.py` 重写，`src/llm/router.py` 删除，`pricing.py` 简化
- **Auth 层**：`src/api/middleware/auth.py`、`src/api/routes/auth.py`、`src/api/auth.py` 全删
- **Paper 层**：`src/agents/strategy_exec/brokers/` 整目录删除，`src/api/routes/paper.py`、`src/models/paper.py`、`src/services/portfolio_service.py` 删除
- **下游牵连**：`position_monitor`、`strategy_exec/agent.py`、`event_bus` 集成测试、宪法 guard、CLI
- **前端**：`web/app/paper/`、`web/app/login/`、`web/lib/auth.ts` 删除，侧边栏补入口
- **配置**：`.env.example` 新建，`src/config.py` 改造，`agent.md` 新建
- **测试**：大量删除 + 适配

## 验收目标
8 道验收门全过：
1. ruff 全绿
2. 禁词扫描 0 命中（LLMProvider / PaperBroker / place_order 等）
3. pytest 全绿
4. 文件名扫描 0 命中（paper / auth / login / jwt）
5. 缺 env 启动失败
6. 配齐 env 启动，API 无需鉴权
7. 前端侧边栏三入口可点击
8. STATE.md + tag + agent.md 同步

## Size: L
## 推断依据
- 范围：跨系统（LLM / auth / paper / web / config / tests），30+ 文件
- 关键词：refactor / remove / redesign
- 依赖变更：删除 paper 牵连 position_monitor / portfolio_service / event_bus / 宪法 guard
- 风险：需全量回归，8 道验收门

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（全部阶段 + post-spec / post-plan / pre-ship gate）

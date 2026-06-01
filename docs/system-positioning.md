# Aegis-Trader 系统定位

## 第一原则

Aegis-Trader 是**交易决策辅助系统**，不是自动交易系统。

- 系统**永不自动下单**
- 所有决策建议仅供参考
- 真实下单由用户在券商 App **手动**完成

## 红线（违反即 GA 阻断）

1. 代码中绝不出现 `submit_order` / `place_order` / `modify_order` / `cancel_order` / `PaperBroker`
2. Web 界面绝不出现"一键下单 / 一键跟单 / 自动执行"按钮
3. Telegram 推送绝不出现"已为您下单"

## 边界

- 仅支持美股（港股已锁定不做）
- 单用户私有部署（无多租户、无登录）
- 桌面 Web 主战场，移动端体验由 Telegram 承接

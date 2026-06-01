# Change: sprint16-branch-F-fixes-and-polish

## 概述
Sprint16 Branch F — 修复 A~E 合入后的 CRITICAL/HIGH/MEDIUM 问题，接入真实 Telegram adapter，打磨前端体验。

## 动机
Branch A~E 已全部合入 master，但代码评审发现多项缺陷：前后端 trace 字段名不匹配、E2E smoke WS 路径错误、PushBanner 未挂载、decisions 列表页缺失、测试 fixture 缺陷、decision_id 时序问题、Signal 面板缺 since 筛选器、X adapter 空占位、PyYAML 未声明依赖。此外需接入真实 Telegram Bot API adapter。

## 影响范围
- **后端 API**: `src/api/routes/decisions.py`（trace 字段名对齐）
- **后端服务**: `src/services/decision_composer.py`（decision_id 时序修复）、`src/signals/x_social/adapter.py`（TODO 标记）
- **后端新增**: `src/services/push_adapters/telegram.py`（真实 Telegram adapter）、`src/config.py`（telegram 配置字段）
- **前端**: `web/app/decisions/[id]/page.tsx`（字段名对齐）、`web/app/decisions/page.tsx`（新建列表页）、`web/app/signals/page.tsx`（since 筛选器）、`web/app/layout.tsx`（PushBanner 挂载）
- **E2E**: `scripts/e2e_smoke.sh`（WS 路径修复）
- **测试**: `tests/api/test_mock_routes.py`（fixture 修复）、`tests/integration/test_decision_pipeline.py`（断言 key 更新）
- **依赖**: `pyproject.toml`（PyYAML 声明）

## 验收目标
- `pytest tests/` Sprint16 相关 0 failed
- `bash scripts/e2e_smoke.sh` 退出码 0
- 浏览器：`/decisions` 列表页可达、trace 三段正确渲染、push toast 出现、signals since 筛选器生效
- `grep -rn "_mock" src/ web/` 无命中
- `bash scripts/constitution_grep.sh` 通过
- Telegram 未配置时 fallback stub，配置时发送成功
- 8 个 commit：F1~F8

## Size: M
## 推断依据
- 范围：跨模块（后端 API + 服务层 + 前端页面 + E2E + 测试 + 配置 + 依赖），~12 文件
- 关键词：fix / add / polish — 多项修复 + 新功能（Telegram adapter）
- 预估文件数：~12
- 依赖变更：仅内部，新增 PyYAML 声明
- 风险：中等，修复精准但涉及多模块联动

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6

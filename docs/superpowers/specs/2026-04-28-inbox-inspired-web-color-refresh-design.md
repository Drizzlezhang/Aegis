# 2026-04-28 Inbox-inspired web color refresh design

## Context
当前 `web/` 前端已经完成一轮 Material Design 风格升级，并已具备 light / dark 主题切换能力。但现有配色仍明显偏向默认 Material 3 紫色系（例如当前主题主色 `#6750A4` 与相关紫调 surface / glow），整体视觉更像通用 M3 模板，而不是一个具有明确品牌气质的生产力产品。

本次任务不再做结构重设计，而是对当前 UI 做一次 **整体配色升级**，参考 **Google Inbox** 的视觉气质：light 主题强调蓝白、纸感、轻盈和高可读性，dark 主题保持同一家族的深蓝灰映射，而不是另起一套视觉语言。

项目约束保持不变：
- 不改业务逻辑、路由、数据流、接口结构
- 不改页面信息架构
- 上涨红、下跌绿的行情颜色语义保持不变
- 当前已完成的 Material 化组件尽量通过 token-first 的方式整体升级

## Goal
将当前 `web` 站点从偏紫的默认 Material 3 配色，升级为 **Google Inbox 风格的蓝白生产力配色系统**，并保持 light / dark 两套主题在品牌语义上一致。

## Success Criteria
- light 主题整体呈现 Google Inbox 风格的蓝白、轻盈、纸感层次
- dark 主题采用深蓝灰映射，和 light 主题保持同一品牌家族
- Header / Sidebar / Card / 表单 / 表格 / 图表容器在配色上统一
- 当前偏紫的主色与辉光感被移除或显著减弱
- 涨跌红绿语义保持不变，继续走 `web/lib/change-color.ts`
- 不引入结构性改动或功能回归
- `npm --prefix web run build` 通过，并完成 light / dark 手动浏览器验收

## Scope
### In scope
- 替换当前主题 token：CSS variables + MUI palette
- 重设 `background` / `surface` / `surface-muted` / `foreground` / `outline` / `primary`
- 调整高频组件对新主题的响应：
  - Header
  - Sidebar
  - card / card-muted
  - Button / Chip / TextField / Paper
  - 表格 hover / selected / outline
  - 图表容器 / tooltip / 非涨跌型主线
- 去掉当前明显偏紫的主色与紫调背景辉光

### Out of scope
- 不改页面布局结构
- 不改业务逻辑、API、路由、状态流
- 不做第二轮大规模组件重写
- 不重写图表数据逻辑
- 不修复 `8003` 后端服务不可达问题
- 不改变行情涨跌颜色语义
- 不新增复杂动效体系

## Visual Direction
采用 **Inbox Classic** 方向：
- light：雾白背景、白卡片、浅蓝灰层级、Inbox 蓝作为品牌主色
- dark：深蓝灰背景与表面、柔和亮蓝作为主色
- 整体气质偏“生产力工具”“收件箱信息卡片”，而不是带紫色品牌辉光的通用 M3 控件集

设计特征：
- 蓝色承担品牌感，但不大面积铺底
- 卡片像“paper sheet”而不是“发光面板”
- 导航存在感低于内容
- 状态色（success / warning / error）只用于功能反馈，不与品牌主蓝抢层级

## Color Token Draft
### Light tokens
- `background`: `#f6f9fc`
- `surface`: `#ffffff`
- `surface-muted`: `#eef3f9`
- `foreground`: `#1f2a37`
- `text-secondary`: `#5f6b7a`
- `primary-main`: `#4285f4`
- `primary-hover`: `#336fd1`
- `primary-soft`: `rgba(66, 133, 244, 0.12)`
- `outline`: `rgba(92, 122, 153, 0.18)`
- `outline-strong`: `rgba(92, 122, 153, 0.30)`
- `hover-layer`: `rgba(66, 133, 244, 0.08)`
- `selected-layer`: `rgba(66, 133, 244, 0.14)`

### Dark tokens
- `background`: `#0f1722`
- `surface`: `#17212d`
- `surface-muted`: `#1d2936`
- `foreground`: `#edf3fb`
- `text-secondary`: `#a8b6c7`
- `primary-main`: `#8ab4f8`
- `primary-hover`: `#a8c7fa`
- `primary-soft`: `rgba(138, 180, 248, 0.16)`
- `outline`: `rgba(168, 182, 199, 0.16)`
- `outline-strong`: `rgba(168, 182, 199, 0.28)`
- `hover-layer`: `rgba(138, 180, 248, 0.10)`
- `selected-layer`: `rgba(138, 180, 248, 0.18)`

### Functional status colors
保留功能状态语义，不和品牌蓝混用：
- success: light `#2e7d32`, dark `#81c995`
- warning: light `#b26a00`, dark `#fbc02d`
- error: light `#c53929`, dark `#f28b82`

### Market color semantics
继续保持：
- 上涨：红
- 下跌：绿

所有行情颜色仍通过 `web/lib/change-color.ts` 管理，不与主题主蓝混用。

## Component Mapping
### Header
- light 下改为轻白 / 雾白顶栏
- dark 下改为深蓝灰顶栏
- 使用极轻底边或低对比分隔，而非重边框
- 顶部导航 active 态改为浅蓝 selected-layer
- theme toggle / locale switcher 更像轻量工具按钮

### Sidebar
- 背景与页面同家族，但比内容区更稳一点
- active 项使用浅蓝选中层
- hover 使用 hover-layer
- watchlist 区域更像导航内分段，而不是独立重面板

### Card / Panel
- `.card`：light 为白卡 + 极淡阴影，dark 为深蓝灰卡片 + 淡边界
- `.card-muted`：使用更轻的蓝灰表面作为次级信息层
- 保留当前圆角体系，但弱化 glass / glow 感

### Button / Chip / Filter
- 主按钮使用 Inbox 蓝
- outlined/secondary 使用蓝灰边界与浅蓝状态层
- 信息类 Chip 尽量轻量，减少高饱和彩块
- warning / error / success 保留语义色

### Form
- TextField / Select 统一到浅蓝灰边界体系
- focus 态使用清晰蓝边框 + soft ring
- 搜索框应更接近 Inbox 搜索工具气质，而非企业后台硬表单

### Table / List
- 表头使用浅灰蓝表面
- 行 hover 使用 hover-layer
- 分割线弱化为轻边界
- 数字和状态列保持清楚，但不加重块背景

### Charts
- 图表容器外层统一为 card 系统
- axis / grid / tooltip 改为蓝灰辅助色
- 非涨跌型主线可用 Inbox 蓝
- 涨跌相关颜色保持项目既有红绿语义

## Key Files
### Must change
- `web/app/globals.css`
- `web/components/theme/AppThemeProvider.tsx`

### High-probability checks
- `web/components/Header.tsx`
- `web/components/Sidebar.tsx`
- `web/components/LocaleSwitcher.tsx`

### Color-only follow-up checks
- `web/components/market-sentiment-banner.tsx`
- `web/components/market-sentiment-inline.tsx`
- `web/components/price-chart.tsx`
- `web/components/gex-chart.tsx`
- `web/components/volume-profile-chart.tsx`

## Implementation Strategy
采用 **token-first** 策略：
1. 先替换 MUI palette 和 CSS variables
2. 观察已 Material 化组件是否自动跟随新主题
3. 只修没有自动跟上的局部颜色硬编码
4. 最后做 light / dark 浏览器验收

该策略可以最大化复用当前已经完成的 Material 化成果，避免再做一轮结构性改造。

## Risks
- 只换 `primary`，不换 `surface/background`，会导致蓝紫混搭和视觉割裂
- light 做成 Inbox，dark 却像另一套主题，会破坏品牌统一性
- 蓝色用太重，会失去 Inbox 的克制与工具感
- 如果误动行情颜色，会破坏项目既有红涨绿跌约束

## Verification
### Automated
- `npm --prefix web run build`

### Manual
至少在 light / dark 下检查：
- `/`
- `/backtest`
- `/memory`

有条件补充：
- `/history`
- `/status`

重点验收：
- theme toggle 前后配色是否保持同一家族
- Header / Sidebar / Card / Form / Chart 容器是否统一
- 是否明显摆脱当前偏紫的默认 M3 气质
- 行情颜色语义是否保持不变

## Completion Standard
本轮完成时应满足：
- 整站主题主色从偏紫迁移到 Inbox 蓝系
- light / dark 视觉语言统一
- 主要页面不需要结构性返工
- 浏览器中能明显看出是一次品牌配色升级，而不是单纯“把紫改蓝”
- 不引入功能回归

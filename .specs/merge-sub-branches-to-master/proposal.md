# Change: merge-sub-branches-to-master

## 概述

将 `aegis-fixes`、`aegis-notify`、`aegis-backtest-v2` 三个子分支按依赖顺序合并至 `master`。

## 动机

三个功能分支已开发完成，需集成到主线：
- `aegis-fixes`：已知 bug 修复，需优先落地避免后续合并冲突
- `aegis-notify`：通知模块，变更量小，快速集成
- `aegis-backtest-v2`：回测引擎 V2，变更量最大，最后合入

## 影响范围

- `master` 分支历史
- `src/` 后端代码（backtest、notification、fixes）
- `tests/` 新增/修改测试
- `.specs/` devkit 产物

## 验收目标

- 三个分支全部无冲突合并到 master
- 合并顺序：fixes → notify → backtest-v2
- 后端回归 ≥700 passed（基于 Sprint 10 基线）
- 前端 tsc 零错误
- 无文件删除
- 保留 --no-ff 合并历史

## Size: L
## 推断依据

- **范围**：跨 3 个 feature 分支，涉及 backtest、notification、bug fixes 多模块
- **关键词**：merge、integrate、backtest-v2
- **预估文件数**：10–30+（backtest-v2 有 7 commits，预估较大）
- **依赖变更**：内部模块间依赖，可能涉及接口变更
- **风险**：冲突解决、回归测试失败需修复
- **project.scale**：L（project.yaml 已判定）

## 阶段序列

0 → 1 → 2 → 3 → 4 → 5 → 6

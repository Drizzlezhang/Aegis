# Verification: sprint4-post-integration-fixes

## 验证时间
2026-05-17T11:30:00+08:00

## 验证模式
5-full（M 级 change，逐条对照 `requirements.md` AC 验证方式）

## 总结
结果：pass

五项 review fixes 已实现，AC 映射验证全部通过。额外尝试 `npm run lint` 时，Next.js 15 的 `next lint` 因项目缺少 ESLint 配置进入交互式初始化提示，未作为阻塞项；SPEC 中声明的前端类型检查与 build 均已通过。

## AC 对账表

| AC | 结果 | 证据 |
|----|------|------|
| AC-1: Next rewrites 包含 `/ws/:path*` 与 `/api/stats/:path*` 到 `localhost:8003` | pass | 代码审查通过；`cd web && npm run build` 通过 |
| AC-2: Stats routes 通过 `Request` 从 `app.state.stats_service` 获取 singleton | pass | 代码审查通过；`python3 -m py_compile src/api/routes/stats.py` 通过；`python3 -m pytest tests/api/test_stats_routes.py -xvs` 通过 |
| AC-3: lifespan 初始化 `stats_service` 并 shutdown realtime manager | pass | 代码审查通过；`python3 -m py_compile src/api/main.py` 通过 |
| AC-4: `RealtimeManager.shutdown()` 清空 subscribers/latest | pass | 代码审查通过；`python3 -m py_compile src/agents/data_harvester/realtime.py` 通过；`python3 -m pytest tests/agents/test_realtime.py -xvs` 通过 |
| AC-5: BacktestResults adapter 将缺失指标设为 `null` | pass | 代码审查通过；`cd web && npx tsc --noEmit` 通过 |
| AC-6: BacktestResults 组件对 `null` 显示 `--` 且不 crash | pass | 代码审查通过；`cd web && npx tsc --noEmit && npm run build` 通过 |
| AC-7: `isStructuredReport` 提取共享 util，两处调用复用 | pass | 代码审查通过；`cd web && npx tsc --noEmit` 通过 |
| AC-8: Sprint4 集成主路径不回归 | pass | `python3 -m pytest tests/integration/test_sprint4_integration.py -xvs` → 9 passed |
| AC-9: 全量测试在已知环境项排除后通过 | pass | `ulimit -n 4096 && python3 -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py` → 615 passed, 40 warnings |

## 命令结果

### 后端编译与目标单测
```text
python3 -m py_compile src/api/routes/stats.py src/api/main.py src/agents/data_harvester/realtime.py
python3 -m pytest tests/api/test_stats_routes.py tests/agents/test_realtime.py -xvs
=> 12 passed, 40 warnings
```

### 前端类型检查
```text
cd web && npx tsc --noEmit
=> pass
```

### 前端 build
```text
cd web && npm run build
=> pass, Next.js compiled and generated 27 static pages
```

### Sprint4 integration regression
```text
python3 -m pytest tests/integration/test_sprint4_integration.py -xvs
=> 9 passed
```

### 全量回归（排除已知环境项）
```text
ulimit -n 4096 && python3 -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py
=> 615 passed, 40 warnings
```

### Lint 说明
```text
cd web && npm run lint
=> blocked: Next.js 15 `next lint` prompts interactively to create ESLint config because this project has no ESLint config.
```

## 失败项或剩余问题
- 无 AC 阻塞项。
- 非阻塞说明：`npm run lint` 当前不是可自动执行的非交互命令；需后续单独初始化 ESLint 配置或迁移到 ESLint CLI 后再纳入自动 gate。

## 建议操作
- 进入 mandatory pre-commit gate。
- 提交建议：`fix(integration): address Sprint 4 review fixes`

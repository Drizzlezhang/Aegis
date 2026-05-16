# Requirements: sprint4-s4-ui-decoupled

## Functional Requirements

### FR1: useWebSocket Hook
- Accept a WebSocket URL (or null) and options.
- Automatically connect on mount and disconnect/cleanup on unmount.
- Implement exponential backoff reconnection (1s, 2s, 4s, 8s, 16s, max 30s).
- Send heartbeat ping every 30s when connected.
- Surface connection status: `connected` | `reconnecting` | `disconnected`.
- Provide `sendMessage` and `reconnect` methods.
- Parse incoming JSON messages; fallback to raw string if parsing fails.

### FR2: RealtimeTicker Component
- Display a horizontal scrollable list of symbol cards.
- Integrate with `useWebSocket` to receive price updates.
- Flash background color on price update (red for up, green for down — China market convention).
- Show connection status chip.
- Support optional volume display.
- Use MUI palette for colors (not hard-coded hex) to respect dark/light theme.

### FR3: AnalysisReport Component
- Render structured report sections via collapsible accordions.
- Default expand only `executive_summary`.
- Provide expand-all / collapse-all buttons.
- Highlight numbers: bold blue for `$xxx`, bold red/green for `xx%`.
- Show Bull/Bear confidence progress bars in `debate_summary` section.
- Share button copies full report text to clipboard.

### FR4: BacktestResults Component
- Show summary stat cards (win rate, avg P&L, max drawdown, trades).
- Render equity curve line chart and monthly returns bar chart using Recharts.
- Render strategy breakdown table.
- All data via props (mock ready).

### FR5: ThemeToggle Component
- Integrate with existing `AppThemeProvider` (add system-preference detection and localStorage persistence).
- Provide toggle button to switch between light and dark.
- Persist preference to localStorage.
- Respect `prefers-color-scheme` when no stored preference exists.

### FR6: i18n Keys
- Add 25+ new keys for realtime, report, backtest, and theme sections.
- Maintain bilingual `zh-CN` / `en` support.
- Update `InteractionMessages` type and `messages` index.

## Non-Functional Requirements
- All components must be client components (`'use client'`).
- Follow existing project patterns (MUI, Recharts, `@/` path alias).
- China market color convention: up = red, down = green.
- No backend code changes.

## Acceptance Criteria & Verification

| ID | AC | Verification |
|---|---|---|
| AC1 | `useWebSocket` connects on mount and cleans up on unmount | Unit test with mock WebSocket server |
| AC2 | `useWebSocket` reconnects with exponential backoff after close | Unit test: close socket, assert reconnect delay |
| AC3 | `useWebSocket` sends heartbeat ping every 30s | Unit test: advance timers, assert ping sent |
| AC4 | `useWebSocket` parses JSON messages and ignores pong | Unit test: send JSON and pong, assert state |
| AC5 | `RealtimeTicker` renders symbol cards and shows status chip | Component test: render with props |
| AC6 | `RealtimeTicker` flashes correct color on price update | Component test: simulate message, assert background style |
| AC7 | `AnalysisReport` expands executive summary by default | Component test: assert accordion expanded |
| AC8 | `AnalysisReport` expand-all/collapse-all works | Component test: click buttons, assert expanded state |
| AC9 | `AnalysisReport` highlights $price and xx% correctly | Component test: inspect rendered HTML |
| AC10 | `BacktestResults` renders summary cards and charts | Component test: render with mock data |
| AC11 | `ThemeToggle` toggles theme and persists to localStorage | Component test: click toggle, assert localStorage |
| AC12 | `ThemeToggle` respects system preference initially | Unit test: mock matchMedia, assert initial mode |
| AC13 | TypeScript compiles without errors | `npx tsc --noEmit` |
| AC14 | Build succeeds | `npm run build` |
| AC15 | All new and existing tests pass | `npx vitest run` |

# Global Bilingual UI (Chinese + English) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add app-wide Chinese and English UI support, defaulting to Chinese-friendly reading while preserving stock tickers and professional abbreviations like QQQ, SPY, GEX, RSI, LEAPS, POC, VAH, and VAL in English.

**Architecture:** Introduce a lightweight app-local i18n layer in the Next.js frontend instead of adding a heavy external i18n framework immediately. Keep translations in structured dictionaries, provide a locale context + provider for client components, and use a small server-side helper for page-level strings so SSR pages and client components can render consistently.

**Tech Stack:** Next.js App Router, React Context, TypeScript, existing app/components structure, optional localStorage for persisted locale.

---

## Scope and constraints

- Support two locales only: `zh-CN` and `en`.
- Default locale should be `zh-CN` for this project.
- Preserve English for:
  - stock codes / ticker symbols (`QQQ`, `SPY`, `NVDA`)
  - strategy and indicator abbreviations (`LEAPS`, `GEX`, `RSI`, `SMA`, `POC`, `VAH`, `VAL`, `VIX`)
  - API field names and route paths
- Translate UI copy, labels, navigation text, empty states, loading/error states, and page metadata.
- Do **not** attempt machine translation of backend-returned dynamic descriptions in this task. Instead, make frontend-owned strings bilingual first and define a follow-up seam for dynamic recommendation text if needed.
- Keep files focused; if any new file trends toward >300 lines, split dictionaries by page/domain.

## File map

**Create:**
- `web/i18n/types.ts` — locale and translation key types
- `web/i18n/messages/common.ts` — shared UI copy (nav, status, generic actions, empty/loading/error)
- `web/i18n/messages/home.ts` — homepage strings
- `web/i18n/messages/market.ts` — market page strings
- `web/i18n/messages/symbol.ts` — symbol detail strings
- `web/i18n/messages/history.ts` — history page strings
- `web/i18n/messages/status.ts` — status page strings
- `web/i18n/messages/backtest.ts` — backtest page strings
- `web/i18n/messages/memory.ts` — memory page strings
- `web/i18n/messages/index.ts` — merged dictionary export
- `web/i18n/get-message.ts` — server-safe translation getter
- `web/components/LocaleProvider.tsx` — client locale context/provider
- `web/components/LocaleSwitcher.tsx` — top-level locale toggle UI
- `web/lib/format.ts` — locale-aware date/number formatting helpers with protected English abbreviations where needed
- `web/tests/i18n/messages.test.ts` — translation coverage test
- `web/tests/i18n/format.test.ts` — formatting behavior test

**Modify:**
- `web/app/layout.tsx` — set document lang, wire provider, metadata localization seam
- `web/components/Header.tsx` — add locale switcher and localized title copy if applicable
- `web/components/Sidebar.tsx` — localize nav/watchlist labels
- `web/app/page.tsx` — localize homepage text
- `web/app/market/page.tsx` — localize market overview text
- `web/app/symbol/[symbol]/page.tsx` — localize page labels while keeping symbols and abbreviations English
- `web/app/history/page.tsx` — localize history page labels
- `web/app/history/[id]/page.tsx` — localize detail labels
- `web/app/status/page.tsx` — localize page wrapper copy
- `web/app/backtest/page.tsx` — localize wrapper copy if any
- `web/app/memory/page.tsx` — localize wrapper copy if any
- `web/components/StatusPanel.tsx` — localize all user-facing text and status badges
- `web/components/SymbolCard.tsx` — localize labels/status copy
- `web/components/BacktestPageContent.tsx` — localize headings, form labels, empty/error/loading states, keep strategy abbreviations English
- `web/components/MemoryPageContent.tsx` — localize headings/search/empty states
- `web/components/AnalysisPanel.tsx` — localize labels, preserve indicators/metrics abbreviations as needed
- `web/components/gex-chart.tsx` — localize explanatory copy but preserve `GEX`, `Call`, `Put` naming if product language decides so
- `web/components/market-index-card.tsx` — locale-aware number formatting
- `web/components/price-chart.tsx` — locale-aware date formatting
- `web/components/volume-profile-chart.tsx` — locale-aware tooltip labels where appropriate
- `web/lib/api.ts` — only if frontend enums/status labels are coupled here (likely no change)
- `web/package.json` — if test script additions are needed

**Test/Verify:**
- `web/tests/i18n/messages.test.ts`
- `web/tests/i18n/format.test.ts`
- `cd web && npm run build`
- manual verification across `/`, `/market`, `/symbol/QQQ`, `/history`, `/status`, `/memory`, `/backtest`

---

### Task 1: Create the i18n foundation

**Files:**
- Create: `web/i18n/types.ts`
- Create: `web/i18n/messages/common.ts`
- Create: `web/i18n/messages/index.ts`
- Create: `web/i18n/get-message.ts`
- Test: `web/tests/i18n/messages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { getMessage } from '@/i18n/get-message';

describe('getMessage', () => {
  it('returns Chinese common labels by default and preserves English abbreviations', () => {
    expect(getMessage('zh-CN', 'common.watchlist')).toBe('自选列表');
    expect(getMessage('zh-CN', 'common.gex')).toBe('GEX');
  });

  it('returns English labels when locale is en', () => {
    expect(getMessage('en', 'common.watchlist')).toBe('Watchlist');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: FAIL because `@/i18n/get-message` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```ts
// web/i18n/types.ts
export type Locale = 'zh-CN' | 'en';

export type MessageTree = {
  common: {
    watchlist: string;
    dashboard: string;
    market: string;
    history: string;
    status: string;
    memory: string;
    backtest: string;
    loading: string;
    error: string;
    search: string;
    gex: string;
  };
};
```

```ts
// web/i18n/messages/common.ts
import type { Locale, MessageTree } from '../types';

export const commonMessages: Record<Locale, MessageTree['common']> = {
  'zh-CN': {
    watchlist: '自选列表',
    dashboard: '仪表盘',
    market: '市场概览',
    history: '历史记录',
    status: '系统状态',
    memory: '记忆系统',
    backtest: '策略回测',
    loading: '加载中...',
    error: '错误',
    search: '搜索',
    gex: 'GEX',
  },
  en: {
    watchlist: 'Watchlist',
    dashboard: 'Dashboard',
    market: 'Market Overview',
    history: 'History',
    status: 'System Status',
    memory: 'Memory',
    backtest: 'Backtest',
    loading: 'Loading...',
    error: 'Error',
    search: 'Search',
    gex: 'GEX',
  },
};
```

```ts
// web/i18n/messages/index.ts
import type { Locale, MessageTree } from '../types';
import { commonMessages } from './common';

export const messages: Record<Locale, MessageTree> = {
  'zh-CN': {
    common: commonMessages['zh-CN'],
  },
  en: {
    common: commonMessages.en,
  },
};
```

```ts
// web/i18n/get-message.ts
import { messages } from './messages';
import type { Locale } from './types';

export function getMessage(locale: Locale, key: 'common.watchlist' | 'common.gex' | 'common.dashboard' | 'common.market' | 'common.history' | 'common.status' | 'common.memory' | 'common.backtest' | 'common.loading' | 'common.error' | 'common.search'): string {
  const [scope, name] = key.split('.') as ['common', keyof (typeof messages)['zh-CN']['common']];
  return messages[locale][scope][name];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/i18n/types.ts web/i18n/messages/common.ts web/i18n/messages/index.ts web/i18n/get-message.ts web/tests/i18n/messages.test.ts
git commit -m "feat: add i18n message foundation"
```

### Task 2: Add locale provider and switcher

**Files:**
- Create: `web/components/LocaleProvider.tsx`
- Create: `web/components/LocaleSwitcher.tsx`
- Modify: `web/app/layout.tsx:1-20`
- Modify: `web/components/Header.tsx`
- Test: `web/tests/i18n/messages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { render, screen } from '@testing-library/react';
import { LocaleProvider } from '@/components/LocaleProvider';
import LocaleSwitcher from '@/components/LocaleSwitcher';

test('renders zh-CN and en switcher options', () => {
  render(
    <LocaleProvider initialLocale="zh-CN">
      <LocaleSwitcher />
    </LocaleProvider>
  );

  expect(screen.getByRole('button', { name: '中文' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'English' })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: FAIL because provider/switcher do not exist.

- [ ] **Step 3: Write minimal implementation**

```tsx
// web/components/LocaleProvider.tsx
'use client';

import { createContext, useContext, useMemo, useState } from 'react';
import type { Locale } from '@/i18n/types';

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ initialLocale, children }: { initialLocale: Locale; children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const value = useMemo(() => ({ locale, setLocale }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error('useLocale must be used within LocaleProvider');
  return value;
}
```

```tsx
// web/components/LocaleSwitcher.tsx
'use client';

import { useLocale } from './LocaleProvider';

export default function LocaleSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <div className="flex gap-2">
      <button type="button" aria-pressed={locale === 'zh-CN'} onClick={() => setLocale('zh-CN')}>中文</button>
      <button type="button" aria-pressed={locale === 'en'} onClick={() => setLocale('en')}>English</button>
    </div>
  );
}
```

```tsx
// web/app/layout.tsx
import { LocaleProvider } from '@/components/LocaleProvider';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-950 text-slate-200">
        <LocaleProvider initialLocale="zh-CN">{children}</LocaleProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/LocaleProvider.tsx web/components/LocaleSwitcher.tsx web/app/layout.tsx web/components/Header.tsx web/tests/i18n/messages.test.ts
git commit -m "feat: add locale provider and switcher"
```

### Task 3: Add locale-aware formatting helpers

**Files:**
- Create: `web/lib/format.ts`
- Modify: `web/components/market-index-card.tsx:1-40`
- Modify: `web/components/price-chart.tsx:1-50`
- Modify: `web/components/volume-profile-chart.tsx:1-100`
- Modify: `web/components/StatusPanel.tsx:90-150`
- Modify: `web/app/market/page.tsx:80-100`
- Modify: `web/app/symbol/[symbol]/page.tsx:70-90`
- Test: `web/tests/i18n/format.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { formatDateTime, formatNumber } from '@/lib/format';

describe('format helpers', () => {
  it('formats numbers in zh-CN locale', () => {
    expect(formatNumber(12345.67, 'zh-CN')).toContain('12');
  });

  it('formats date labels without translating stock abbreviations', () => {
    expect(formatDateTime('2026-04-26T10:30:00Z', 'en')).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/format.test.ts`
Expected: FAIL because formatter helper does not exist.

- [ ] **Step 3: Write minimal implementation**

```ts
// web/lib/format.ts
import type { Locale } from '@/i18n/types';

export function formatNumber(value: number, locale: Locale, options?: Intl.NumberFormatOptions) {
  return new Intl.NumberFormat(locale, options).format(value);
}

export function formatDateTime(value: string | number | Date, locale: Locale, options?: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat(locale, options).format(new Date(value));
}
```

Then replace hardcoded `en-US` usages with these helpers.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run tests/i18n/format.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/lib/format.ts web/components/market-index-card.tsx web/components/price-chart.tsx web/components/volume-profile-chart.tsx web/components/StatusPanel.tsx web/app/market/page.tsx web/app/symbol/[symbol]/page.tsx web/tests/i18n/format.test.ts
git commit -m "feat: localize number and date formatting"
```

### Task 4: Localize global shell and navigation

**Files:**
- Modify: `web/components/Header.tsx`
- Modify: `web/components/Sidebar.tsx`
- Modify: `web/app/layout.tsx`
- Modify: `web/i18n/messages/common.ts`
- Test: `web/tests/i18n/messages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { render, screen } from '@testing-library/react';
import Sidebar from '@/components/Sidebar';
import { LocaleProvider } from '@/components/LocaleProvider';

test('shows Chinese navigation labels in zh-CN', () => {
  render(
    <LocaleProvider initialLocale="zh-CN">
      <Sidebar symbols={[]} />
    </LocaleProvider>
  );

  expect(screen.getByText('自选列表')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: FAIL because sidebar text is still hardcoded in English.

- [ ] **Step 3: Write minimal implementation**

Apply locale lookups in shell components and add missing common keys:

```ts
// extend common messages
{
  navHome: '首页',
  navMarket: '市场',
  navHistory: '历史',
  navStatus: '状态',
  navMemory: '记忆',
  navBacktest: '回测',
}
```

Then replace hardcoded labels in `Header.tsx` and `Sidebar.tsx` with translator lookups.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/Header.tsx web/components/Sidebar.tsx web/app/layout.tsx web/i18n/messages/common.ts web/tests/i18n/messages.test.ts
git commit -m "feat: localize app shell navigation"
```

### Task 5: Localize page-level static copy

**Files:**
- Create: `web/i18n/messages/home.ts`
- Create: `web/i18n/messages/market.ts`
- Create: `web/i18n/messages/history.ts`
- Create: `web/i18n/messages/status.ts`
- Create: `web/i18n/messages/backtest.ts`
- Create: `web/i18n/messages/memory.ts`
- Modify: `web/app/page.tsx`
- Modify: `web/app/market/page.tsx`
- Modify: `web/app/history/page.tsx`
- Modify: `web/app/history/[id]/page.tsx`
- Modify: `web/app/status/page.tsx`
- Modify: `web/app/backtest/page.tsx`
- Modify: `web/app/memory/page.tsx`
- Test: `web/tests/i18n/messages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { getMessage } from '@/i18n/get-message';

test('provides Chinese home and market headings', () => {
  expect(getMessage('zh-CN', 'home.title')).toBe('仪表盘');
  expect(getMessage('zh-CN', 'market.title')).toBe('市场概览');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: FAIL because `home.title` and `market.title` do not exist.

- [ ] **Step 3: Write minimal implementation**

Add page message files and update `getMessage`/message typing so these keys resolve. Replace hardcoded page headings/subtitles with message lookups.

Example dictionary entry:

```ts
export const homeMessages = {
  'zh-CN': {
    title: '仪表盘',
    subtitle: '多 Agent 量化交易工作台',
    marketIndices: '市场指数',
    systemStatus: '系统状态',
  },
  en: {
    title: 'Dashboard',
    subtitle: 'Multi-agent quantitative trading workspace',
    marketIndices: 'Market Indices',
    systemStatus: 'System Status',
  },
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/i18n/messages/home.ts web/i18n/messages/market.ts web/i18n/messages/history.ts web/i18n/messages/status.ts web/i18n/messages/backtest.ts web/i18n/messages/memory.ts web/app/page.tsx web/app/market/page.tsx web/app/history/page.tsx web/app/history/[id]/page.tsx web/app/status/page.tsx web/app/backtest/page.tsx web/app/memory/page.tsx web/tests/i18n/messages.test.ts
git commit -m "feat: localize page-level static copy"
```

### Task 6: Localize interactive components and preserve abbreviations

**Files:**
- Create: `web/i18n/messages/symbol.ts`
- Modify: `web/app/symbol/[symbol]/page.tsx`
- Modify: `web/components/SymbolCard.tsx`
- Modify: `web/components/StatusPanel.tsx`
- Modify: `web/components/BacktestPageContent.tsx`
- Modify: `web/components/MemoryPageContent.tsx`
- Modify: `web/components/AnalysisPanel.tsx`
- Modify: `web/components/gex-chart.tsx`
- Test: `web/tests/i18n/messages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { getMessage } from '@/i18n/get-message';

test('keeps domain abbreviations in English inside Chinese copy', () => {
  expect(getMessage('zh-CN', 'symbol.gexWalls')).toBe('GEX 墙');
  expect(getMessage('zh-CN', 'backtest.rsi')).toBe('RSI');
  expect(getMessage('zh-CN', 'backtest.smaRsiCombo')).toBe('SMA + RSI 组合');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: FAIL because symbol/backtest message keys do not exist.

- [ ] **Step 3: Write minimal implementation**

Add component-specific dictionaries and replace hardcoded English labels in these components. Preserve the following terms in English in both locales where appropriate:
- `LEAPS`
- `Bull Spread`
- `Covered Call`
- `GEX`
- `RSI`
- `SMA`
- `POC`
- `VAH`
- `VAL`
- ticker symbols

Examples:

```ts
// zh-CN examples
{
  gexWalls: 'GEX 墙',
  tradeHistory: '交易历史',
  signalType: '信号类型',
  smaRsiCombo: 'SMA + RSI 组合',
  leapsCall: 'LEAPS Call',
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/i18n/messages/symbol.ts web/app/symbol/[symbol]/page.tsx web/components/SymbolCard.tsx web/components/StatusPanel.tsx web/components/BacktestPageContent.tsx web/components/MemoryPageContent.tsx web/components/AnalysisPanel.tsx web/components/gex-chart.tsx web/tests/i18n/messages.test.ts
git commit -m "feat: localize interactive trading components"
```

### Task 7: Persist locale and polish metadata/manual verification

**Files:**
- Modify: `web/components/LocaleProvider.tsx`
- Modify: `web/app/layout.tsx`
- Modify: page metadata definitions as needed
- Test: `web/tests/i18n/messages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { render } from '@testing-library/react';
import { LocaleProvider } from '@/components/LocaleProvider';

test('uses zh-CN as the default locale', () => {
  const view = render(<LocaleProvider initialLocale="zh-CN"><div>ok</div></LocaleProvider>);
  expect(view.container).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts`
Expected: FAIL if provider persistence/default logic is not implemented yet.

- [ ] **Step 3: Write minimal implementation**

Enhance `LocaleProvider` to:
- default to `zh-CN`
- read saved locale from `localStorage`
- persist locale changes
- keep `<html lang>` synchronized on the client

Example persistence logic:

```tsx
useEffect(() => {
  const saved = window.localStorage.getItem('locale');
  if (saved === 'zh-CN' || saved === 'en') {
    setLocale(saved);
  }
}, []);

useEffect(() => {
  window.localStorage.setItem('locale', locale);
  document.documentElement.lang = locale;
}, [locale]);
```

- [ ] **Step 4: Run test and build to verify it passes**

Run: `cd web && npx vitest run tests/i18n/messages.test.ts tests/i18n/format.test.ts`
Expected: PASS

Run: `cd web && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/components/LocaleProvider.tsx web/app/layout.tsx web/tests/i18n/messages.test.ts web/tests/i18n/format.test.ts
git commit -m "feat: persist locale preference"
```

---

## Manual verification checklist

- [ ] Visit `/` and confirm default UI is Chinese while `QQQ`, `SPY`, `GEX` remain English.
- [ ] Toggle to English from the header and confirm nav/page text updates.
- [ ] Refresh the page and confirm locale preference persists.
- [ ] Visit `/symbol/QQQ` and confirm labels translate but ticker + abbreviations remain English.
- [ ] Visit `/backtest` and confirm `RSI`, `SMA`, `LEAPS`, `Bull Spread`, `Covered Call` stay English.
- [ ] Visit `/memory` and confirm search/loading/empty states translate.
- [ ] Visit `/status` and confirm health/status labels translate correctly.
- [ ] Run `cd web && npm run build` and confirm build passes.

## Risks and decisions

1. **Server vs client locale source**
   - Initial version can keep locale primarily client-side with `zh-CN` default.
   - If SSR-perfect locale rendering is needed later, add cookie-based locale negotiation in a follow-up.

2. **Dynamic backend-generated text**
   - Recommendations and reports coming directly from backend may remain English for now.
   - A later phase can move recommendation templates into structured bilingual fields or frontend-generated localized labels.

3. **Test setup gap**
   - If `vitest` / Testing Library are not present in `web/package.json`, add them in the first execution task rather than introducing a broader test framework migration.

4. **Abbreviation policy**
   - Treat domain abbreviations as product terms, not translatable strings.
   - Chinese copy should wrap them naturally, e.g. `GEX 墙`, `RSI 信号`, `LEAPS Call`.

## Self-review

- Spec coverage: plan includes global shell, page copy, interactive components, formatting, persistence, and abbreviation preservation.
- Placeholder scan: all tasks name exact files, exact tests, exact commands, and concrete implementation examples.
- Type consistency: locale type is fixed to `zh-CN | en`; message access stays centralized through `getMessage`; abbreviation policy is consistent across tasks.

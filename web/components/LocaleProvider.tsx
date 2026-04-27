'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { readStoredLocale, syncDocumentLang, writeStoredLocale } from '@/i18n/locale-storage';
import type { Locale } from '@/i18n/types';

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale;
  children: React.ReactNode;
}) {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const value = useMemo(() => ({ locale, setLocale }), [locale]);

  useEffect(() => {
    setLocale(readStoredLocale(initialLocale));
  }, [initialLocale]);

  useEffect(() => {
    writeStoredLocale(locale);
    syncDocumentLang(locale);
  }, [locale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) {
    throw new Error('useLocale must be used within LocaleProvider');
  }
  return value;
}

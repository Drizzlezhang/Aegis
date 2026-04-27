import type { Locale } from './types';

const LOCALE_STORAGE_KEY = 'aegis-locale';
const SUPPORTED_LOCALES: Locale[] = ['zh-CN', 'en'];

export function readStoredLocale(initialLocale: Locale): Locale {
  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  return isLocale(stored) ? stored : initialLocale;
}

export function writeStoredLocale(locale: Locale): void {
  window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
}

export function syncDocumentLang(locale: Locale): void {
  document.documentElement.lang = locale;
}

function isLocale(value: string | null): value is Locale {
  return value !== null && SUPPORTED_LOCALES.includes(value as Locale);
}

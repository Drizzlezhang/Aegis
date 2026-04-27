import { describe, expect, it } from 'vitest';
import { readStoredLocale, syncDocumentLang, writeStoredLocale } from '@/i18n/locale-storage';

describe('locale storage helpers', () => {
  it('reads a stored locale when it is supported', () => {
    window.localStorage.setItem('aegis-locale', 'en');

    expect(readStoredLocale('zh-CN')).toBe('en');
  });

  it('falls back to the initial locale when storage is empty or invalid', () => {
    window.localStorage.removeItem('aegis-locale');
    expect(readStoredLocale('zh-CN')).toBe('zh-CN');

    window.localStorage.setItem('aegis-locale', 'fr');
    expect(readStoredLocale('zh-CN')).toBe('zh-CN');
  });

  it('writes locale to localStorage', () => {
    writeStoredLocale('en');

    expect(window.localStorage.getItem('aegis-locale')).toBe('en');
  });

  it('syncs the html lang attribute', () => {
    document.documentElement.lang = 'zh-CN';

    syncDocumentLang('en');

    expect(document.documentElement.lang).toBe('en');
  });
});

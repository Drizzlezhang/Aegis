'use client';

import { useLocale } from './LocaleProvider';

export default function LocaleSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <div className="flex items-center gap-2 text-xs">
      <button
        type="button"
        aria-pressed={locale === 'zh-CN'}
        onClick={() => setLocale('zh-CN')}
        className={`rounded px-2 py-1 transition-colors ${locale === 'zh-CN' ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'}`}
      >
        中文
      </button>
      <button
        type="button"
        aria-pressed={locale === 'en'}
        onClick={() => setLocale('en')}
        className={`rounded px-2 py-1 transition-colors ${locale === 'en' ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'}`}
      >
        English
      </button>
    </div>
  );
}

import { messages } from './messages';
import type { Locale, MessageKey } from './types';

export function getMessage(locale: Locale, key: MessageKey): string {
  const [scope, name] = key.split('.') as [keyof typeof messages['zh-CN'], string];
  return (messages[locale][scope] as Record<string, string>)[name];
}

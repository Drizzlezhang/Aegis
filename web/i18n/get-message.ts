import { messages } from './messages';
import type { Locale, MessageKey } from './types';

export function getMessage(locale: Locale, key: MessageKey): string {
  const [scope, name] = key.split('.') as [keyof Pick<typeof messages['zh-CN'], 'common' | 'interaction'>, string];
  return messages[locale][scope][name as keyof (typeof messages)[typeof locale][typeof scope]];
}

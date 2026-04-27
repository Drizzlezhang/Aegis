import type { Locale, MessageTree } from '../types';
import { backtestMessages } from './backtest';
import { commonMessages } from './common';
import { historyMessages } from './history';
import { homeMessages } from './home';
import { interactionMessages } from './interaction';
import { marketMessages } from './market';
import { memoryMessages } from './memory';
import { statusMessages } from './status';

export const messages: Record<Locale, MessageTree> = {
  'zh-CN': {
    common: commonMessages['zh-CN'],
    interaction: interactionMessages['zh-CN'],
    home: homeMessages['zh-CN'],
    marketPage: marketMessages['zh-CN'],
    statusPage: statusMessages['zh-CN'],
    historyPage: historyMessages['zh-CN'],
    memoryPage: memoryMessages['zh-CN'],
    backtestPage: backtestMessages['zh-CN'],
  },
  en: {
    common: commonMessages.en,
    interaction: interactionMessages.en,
    home: homeMessages.en,
    marketPage: marketMessages.en,
    statusPage: statusMessages.en,
    historyPage: historyMessages.en,
    memoryPage: memoryMessages.en,
    backtestPage: backtestMessages.en,
  },
};

export type Locale = 'zh-CN' | 'en';

export type CommonMessages = {
  watchlist: string;
  navigation: string;
  dashboard: string;
  market: string;
  analyze: string;
  history: string;
  status: string;
  memory: string;
  backtest: string;
  loading: string;
  error: string;
  search: string;
  gex: string;
};

export type InteractionMessages = {
  searching: string;
  healthOverview: string;
  vol: string;
  rsi: string;
  smaRsiCombo: string;
  leapsCall: string;
  loadingSystemStatus: string;
  failedToLoadSystemStatus: string;
  allSystemsOperational: string;
  issuesDetected: string;
  done: string;
  pending: string;
  bearish: string;
  neutral: string;
  bullish: string;
  agents: string;
  skills: string;
  loaded: string;
  systemInfo: string;
  version: string;
  uptime: string;
  memory: string;
  python: string;
  lastRun: string;
  runs: string;
  loadingMemory: string;
  analysisResults: string;
  marketNotes: string;
  tradingActions: string;
  embeddingDim: string;
  semanticSearch: string;
  searchAnalysisResults: string;
  noResultsFound: string;
  noMarketNotesYet: string;
  general: string;
  backtestFailed: string;
  configuration: string;
  strategy: string;
  signalType: string;
  startDate: string;
  endDate: string;
  running: string;
  runBacktest: string;
  totalReturn: string;
  annualized: string;
  winRate: string;
  profitFactor: string;
  maxDrawdown: string;
  sharpeRatio: string;
  equityCurve: string;
  monthlyReturns: string;
  tradeStatistics: string;
  tradeHistory: string;
  totalTrades: string;
  winningTrades: string;
  losingTrades: string;
  averageWin: string;
  averageLoss: string;
  bestTrade: string;
  worstTrade: string;
  date: string;
  price: string;
  return: string;
  showingTrades: string;
};

export type MessageTree = {
  common: CommonMessages;
  interaction: InteractionMessages;
  home: {
    title: string;
    subtitle: string;
    marketIndices: string;
    systemStatus: string;
    agents: string;
    skills: string;
    lastUpdate: string;
    lastUpdateValue: string;
    active: string;
    loaded: string;
  };
  marketPage: {
    title: string;
    subtitle: string;
    error: string;
    marketSentiment: string;
    vixLevel: string;
    positionSizing: string;
    noData: string;
  };
  statusPage: {
    title: string;
    subtitle: string;
  };
  historyPage: {
    title: string;
    subtitle: string;
  };
  memoryPage: {
    title: string;
    subtitle: string;
  };
  backtestPage: {
    title: string;
    subtitle: string;
  };
};

export type CommonMessageKey = `common.${keyof CommonMessages}`;
export type InteractionMessageKey = `interaction.${keyof InteractionMessages}`;
export type MessageKey = CommonMessageKey | InteractionMessageKey;

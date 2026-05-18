import { getServerApiBase } from '@/utils/server-api-base';
import { getToken } from '@/lib/auth';

function getAuthHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function resolveApiBase(): string {
  if (typeof window !== 'undefined') {
    return '';
  }

  return getServerApiBase();
}

function buildApiUrl(path: string): string {
  const base = resolveApiBase();
  return `${base}${path}`;
}

export interface SymbolInfo {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  trend: 'up' | 'down' | 'neutral';
  analysisStatus: 'completed' | 'pending' | 'error';
}

export interface SupportResistance {
  level: number;
  type: 'support' | 'resistance';
  strength: 'weak' | 'moderate' | 'strong';
  source: string;
}

export interface VolumeProfile {
  poc: number;
  vah: number;
  val: number;
  volumeAtPoc: number;
}

export interface GexWall {
  strike: number;
  gamma: number;
  type: 'call' | 'put';
  strength: 'weak' | 'moderate' | 'strong';
}

export interface StrategyRecommendation {
  id: string;
  type: 'LEAPS' | 'Bull Spread' | 'Covered Call' | 'Cash Secured Put';
  description: string;
  riskLevel: 'low' | 'medium' | 'high';
  expectedReturn: string;
  expiration?: string;
  strike?: string;
}

export interface SymbolDetail {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  avgVolume: number;
  marketCap: string;
  peRatio: number;
  supports: SupportResistance[];
  resistances: SupportResistance[];
  volumeProfile: VolumeProfile;
  gexWalls: GexWall[];
  recommendations: StrategyRecommendation[];
}

export interface HistoryEntry {
  id: number;
  symbol: string;
  tradeDate: string;
  agentSequence: string[];
  recommendationsCount: number;
  executionTime: number;
  success: boolean;
}

export interface AgentStatus {
  name: string;
  status: string;
  lastRun: string;
  executions: number;
}

export interface SkillStatus {
  name: string;
  type: string;
  loaded: boolean;
}

export interface SystemInfo {
  version: string;
  uptime: string;
  memoryUsage: string;
  pythonVersion: string;
  nodeVersion: string;
}

export interface HealthStatus {
  data_harvester: boolean;
  quant_brain: boolean;
  strategy_exec: boolean;
  aegis_memory: boolean;
  llm_router: boolean;
  vector_store: boolean;
}

export interface LlmMetrics {
  requests: number;
  tokens: number;
  errors: number;
}

export interface PipelineMetrics {
  agents: string[];
  total_runs: number;
  last_run_time: string | null;
  avg_duration_seconds: number;
  llm: LlmMetrics;
}

export interface StatusData {
  agents: AgentStatus[];
  skills: SkillStatus[];
  system: SystemInfo;
  health: HealthStatus;
  pipeline: PipelineMetrics;
}

export interface MarketIndexData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  timestamp: string;
  market: string;
}

export interface MarketIndicesResponse {
  indices: MarketIndexData[];
  count: number;
  error?: string;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const requestUrl = buildApiUrl(path);
  const res = await fetch(requestUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error for ${path}: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getSymbols(): Promise<SymbolInfo[]> {
  return fetchApi<SymbolInfo[]>('/api/symbols');
}

export async function getSymbolDetail(symbol: string): Promise<SymbolDetail> {
  return fetchApi<SymbolDetail>(`/api/symbols/${encodeURIComponent(symbol)}`);
}

export async function getSymbolAnalysis(symbol: string): Promise<Record<string, unknown>> {
  return fetchApi<Record<string, unknown>>(`/api/symbols/${encodeURIComponent(symbol)}/analysis`);
}

export async function getAnalysisHistory(symbol?: string, limit = 20): Promise<HistoryEntry[]> {
  const params = new URLSearchParams();
  if (symbol) params.set('symbol', symbol);
  params.set('limit', String(limit));
  return fetchApi<HistoryEntry[]>(`/api/analysis?${params.toString()}`);
}

export interface AnalysisDetail {
  id: number;
  symbol: string;
  tradeDate: string;
  agentSequence: string[];
  recommendations: Array<{
    type: string;
    strike: number;
    expiry: string;
    entry_price: number;
    confidence: number;
    [key: string]: unknown;
  }>;
  actionReport: string;
  metadata?: Record<string, unknown>;
  executionTime: number;
  success: boolean;
  createdAt: string;
}

export async function getAnalysisDetail(id: number): Promise<AnalysisDetail> {
  return fetchApi<AnalysisDetail>(`/api/analysis/${id}`);
}

export async function getStatus(): Promise<StatusData> {
  return fetchApi<StatusData>('/api/status');
}

export async function getPositionSummary(): Promise<PositionSummaryData> {
  return fetchApi<PositionSummaryData>('/api/positions/summary');
}

export async function getPositionAlerts(): Promise<PositionAlertsResponse> {
  return fetchApi<PositionAlertsResponse>('/api/positions/alerts');
}

export async function getPositionChain(positionId: string): Promise<PositionChainItem[]> {
  return fetchApi<PositionChainItem[]>(`/api/positions/${encodeURIComponent(positionId)}/chain`);
}

export async function getMarketIndices(): Promise<MarketIndicesResponse> {
  return fetchApi<MarketIndicesResponse>('/api/market/indices');
}

// Backtest types
export interface BacktestConfigPayload {
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  short_window?: number;
  long_window?: number;
  strategy?: string;
  signal_type?: string;
  rsi_period?: number;
  rsi_overbought?: number;
  rsi_oversold?: number;
}

export interface BacktestTrade {
  date: string;
  type: 'entry' | 'exit';
  price: number;
  pnl: number | null;
  pnlPercent: number | null;
}

export interface BacktestMetricsData {
  totalReturn: number;
  annualizedReturn: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  sharpeRatio: number;
  totalTrades: number;
  avgWin: number;
  avgLoss: number;
  bestTrade: number;
  worstTrade: number;
}

export interface MonthlyReturnData {
  month: string;
  return: number;
}

export interface EquityPoint {
  date: string;
  value: number;
  benchmark: number;
}

export interface BacktestApiResult {
  symbol: string;
  strategy: string;
  equityCurve: EquityPoint[];
  trades: BacktestTrade[];
  metrics: BacktestMetricsData;
  monthlyReturns: MonthlyReturnData[];
}

// Analyze types
export interface AnalysisRecommendation {
  type: string;
  contractSymbol: string;
  strike: number;
  expiry: string;
  entryPrice: number;
  targetPrice: number | null;
  stopLoss: number | null;
  riskRewardRatio: number | null;
  confidence: number;
  reasoning: string;
}

export interface AnalysisResult {
  symbol: string;
  status: string;
  agentSequence: string[];
  recommendationsCount: number;
  executionTime: number;
  report: string;
  recommendations: AnalysisRecommendation[];
  metadata?: Record<string, unknown>;
}

export interface AnalysisResponse {
  results: AnalysisResult[];
  totalTime: number;
}

export interface AnalysisStreamProgressEvent {
  symbol: string;
  stage: string;
  step: number;
  totalSteps: number;
  progress: number;
}

export interface AnalysisStreamResultEvent {
  result: AnalysisResult;
  progress: number;
}

export interface AnalysisStreamStepEvent {
  symbol: string;
  agentSequence: string[];
  currentStep: number;
  totalSteps: number;
}

export interface PositionData {
  id: string;
  symbol: string;
  status: 'planned' | 'active' | 'rolled' | 'closed' | 'expired';
  strike: number;
  expiry: string;
  dte: number;
  entry_price: number;
  current_price: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  quantity: number;
}

export interface PositionSummaryData {
  total_positions: number;
  active_count: number;
  closed_count: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  positions: PositionData[];
}

export interface PositionChainAction {
  action_type: string;
  date: string;
  price: number;
  quantity: number;
  notes: string;
}

export interface PositionChainItem {
  id: string;
  symbol: string;
  status: 'planned' | 'active' | 'rolled' | 'closed' | 'expired';
  entry_date: string;
  close_date: string | null;
  entry_price: number;
  current_price: number | null;
  actions: PositionChainAction[];
}

export interface PositionAlertData {
  type: string;
  position_id: string;
  symbol: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
  suggested_action: string;
}

export interface PositionAlertsResponse {
  alerts: PositionAlertData[];
  scanned_at: string;
}

export async function loadSymbolPageData(
  symbol: string,
  deps: {
    getSymbolDetail: typeof getSymbolDetail;
    getMarketIndices: typeof getMarketIndices;
    getSymbols: typeof getSymbols;
  } = {
    getSymbolDetail,
    getMarketIndices,
    getSymbols,
  }
): Promise<{
  detail: SymbolDetail;
  indices: MarketIndexData[];
  symbols: SymbolInfo[];
}> {
  const detailPromise = deps.getSymbolDetail(symbol.toUpperCase());
  const indicesPromise = deps.getMarketIndices();
  const symbolsPromise = deps.getSymbols();

  const [detailResult, indicesResult, symbolsResult] = await Promise.allSettled([
    detailPromise,
    indicesPromise,
    symbolsPromise,
  ]);

  if (detailResult.status !== 'fulfilled') {
    throw detailResult.reason;
  }

  return {
    detail: detailResult.value,
    indices: indicesResult.status === 'fulfilled' ? indicesResult.value.indices || [] : [],
    symbols: symbolsResult.status === 'fulfilled' ? symbolsResult.value : [],
  };
}

export async function runAnalysis(symbols: string[]): Promise<AnalysisResponse> {
  return fetchApi<AnalysisResponse>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ symbols }),
  });
}

export async function runAnalysisStream(
  symbols: string[],
  handlers: {
    onStart?: (payload: { symbols: string[]; progress: number }) => void;
    onProgress?: (payload: AnalysisStreamProgressEvent) => void;
    onStep?: (payload: AnalysisStreamStepEvent) => void;
    onResult?: (payload: AnalysisStreamResultEvent) => void;
    onDone?: (payload: { totalTime: number; progress: number }) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(buildApiUrl('/api/analyze/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ symbols }),
      signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`API error for /api/analyze/stream: ${response.status} ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const dispatchEvent = (chunk: string) => {
      const lines = chunk.split('\n');
      let eventName = 'message';
      const dataLines: string[] = [];

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim());
        }
      }

      if (dataLines.length === 0) {
        return;
      }

      const payload = JSON.parse(dataLines.join('\n'));
      if (eventName === 'start') handlers.onStart?.(payload);
      if (eventName === 'progress') handlers.onProgress?.(payload);
      if (eventName === 'step') handlers.onStep?.(payload);
      if (eventName === 'result') handlers.onResult?.(payload);
      if (eventName === 'done') handlers.onDone?.(payload);
      if (eventName === 'error') {
        throw new Error(payload.message || 'Analysis stream failed');
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const eventChunk of events) {
        if (eventChunk.trim()) {
          dispatchEvent(eventChunk);
        }
      }
    }

    if (buffer.trim()) {
      dispatchEvent(buffer);
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      return;
    }
    throw err;
  }
}

export async function runBacktest(config: BacktestConfigPayload): Promise<BacktestApiResult> {
  return fetchApi<BacktestApiResult>('/api/backtest', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export interface TradingStatsData {
  total_decisions: number;
  total_positions: number;
  win_rate: number;
  avg_pnl_pct: number;
  total_realized_pnl: number;
  best_trade: Record<string, unknown> | null;
  worst_trade: Record<string, unknown> | null;
  avg_holding_days: number;
  monthly_pnl: Record<string, number>;
  by_strategy: Record<string, unknown>;
  by_symbol: Record<string, unknown>;
}

export interface StrategyPerformanceData {
  strategy_type: string;
  count: number;
  win_rate: number;
  avg_pnl: number;
  [key: string]: unknown;
}

export async function getTradingStats(days = 90): Promise<TradingStatsData> {
  return fetchApi<TradingStatsData>(`/api/stats/trading?days=${days}`);
}

export async function getStrategyPerformance(): Promise<StrategyPerformanceData[]> {
  return fetchApi<StrategyPerformanceData[]>('/api/stats/strategy-performance');
}

// Memory types
export interface MemorySearchResult {
  id: number;
  document: string;
  metadata: Record<string, unknown>;
  similarity_score: number;
}

export interface MemorySearchResponse {
  results: MemorySearchResult[];
  query: string;
  count: number;
}

export interface MarketNoteItem {
  id: number;
  symbol: string | null;
  note_date: string;
  category: string;
  content: string;
  tags: string[];
  created_at: string;
}

export interface MemoryStats {
  analysis_results: number;
  market_notes: number;
  trading_actions: number;
  total: number;
  embedding_dimension: number;
  storage_path: string;
}

export async function searchMemory(query: string, symbol?: string, limit = 5): Promise<MemorySearchResponse> {
  return fetchApi<MemorySearchResponse>('/api/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query, symbol, limit }),
  });
}

export async function getMarketNotes(symbol?: string, category?: string, limit = 20): Promise<MarketNoteItem[]> {
  const params = new URLSearchParams();
  if (symbol) params.set('symbol', symbol);
  if (category) params.set('category', category);
  params.set('limit', String(limit));
  return fetchApi<MarketNoteItem[]>(`/api/memory/notes?${params.toString()}`);
}

export async function getMemoryStats(): Promise<MemoryStats> {
  return fetchApi<MemoryStats>('/api/memory/stats');
}

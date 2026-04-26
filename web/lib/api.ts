const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8003';

function resolveApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }
  return DEFAULT_API_ORIGIN;
}

const API_BASE = resolveApiBase();

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

export interface StatusData {
  agents: AgentStatus[];
  skills: SkillStatus[];
  system: SystemInfo;
  health: HealthStatus;
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
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
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
}

export interface AnalysisResponse {
  results: AnalysisResult[];
  totalTime: number;
}

export async function runAnalysis(symbols: string[]): Promise<AnalysisResponse> {
  return fetchApi<AnalysisResponse>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ symbols }),
  });
}

export async function runBacktest(config: BacktestConfigPayload): Promise<BacktestApiResult> {
  return fetchApi<BacktestApiResult>('/api/backtest', {
    method: 'POST',
    body: JSON.stringify(config),
  });
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

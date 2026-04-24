import { NextResponse } from 'next/server';

const HISTORY = [
  {
    id: 1,
    symbol: 'QQQ',
    tradeDate: '2026-04-24',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 3,
    executionTime: 12.5,
    success: true,
  },
  {
    id: 2,
    symbol: 'SPY',
    tradeDate: '2026-04-24',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 2,
    executionTime: 11.8,
    success: true,
  },
  {
    id: 3,
    symbol: 'NVDA',
    tradeDate: '2026-04-24',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 3,
    executionTime: 14.2,
    success: true,
  },
  {
    id: 4,
    symbol: 'AAPL',
    tradeDate: '2026-04-23',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 0,
    executionTime: 10.5,
    success: true,
  },
  {
    id: 5,
    symbol: 'INTC',
    tradeDate: '2026-04-23',
    agentSequence: ['Data-Harvester'],
    recommendationsCount: 0,
    executionTime: 2.1,
    success: false,
  },
  {
    id: 6,
    symbol: 'TSLA',
    tradeDate: '2026-04-22',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 2,
    executionTime: 13.7,
    success: true,
  },
  {
    id: 7,
    symbol: 'PLTR',
    tradeDate: '2026-04-22',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 3,
    executionTime: 12.9,
    success: true,
  },
  {
    id: 8,
    symbol: 'KO',
    tradeDate: '2026-04-21',
    agentSequence: ['Data-Harvester', 'Quant-Brain', 'Strategy-Execution', 'Aegis-Memory'],
    recommendationsCount: 1,
    executionTime: 11.2,
    success: true,
  },
];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol');
  const limit = parseInt(searchParams.get('limit') || '20', 10);

  let results = HISTORY;
  if (symbol) {
    results = results.filter((r) => r.symbol === symbol.toUpperCase());
  }
  results = results.slice(0, limit);

  return NextResponse.json(results);
}

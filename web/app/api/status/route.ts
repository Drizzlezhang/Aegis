import { NextResponse } from 'next/server';

export async function GET() {
  const status = {
    agents: [
      { name: 'Data-Harvester', status: 'idle', lastRun: '2026-04-24T10:30:00Z', executions: 42 },
      { name: 'Quant-Brain', status: 'idle', lastRun: '2026-04-24T10:30:05Z', executions: 42 },
      { name: 'Strategy-Execution', status: 'idle', lastRun: '2026-04-24T10:30:08Z', executions: 42 },
      { name: 'Aegis-Memory', status: 'idle', lastRun: '2026-04-24T10:30:10Z', executions: 42 },
    ],
    skills: [
      { name: 'yfinance_ohlcv', type: 'data_source', loaded: true },
      { name: 'volume_profile', type: 'algorithm', loaded: true },
      { name: 'gex_calculator', type: 'algorithm', loaded: true },
    ],
    system: {
      version: '0.1.0',
      uptime: '3d 12h 45m',
      memoryUsage: '128MB / 512MB',
      pythonVersion: '3.13.0',
      nodeVersion: '25.6.1',
    },
    health: {
      data_harvester: true,
      quant_brain: true,
      strategy_exec: true,
      aegis_memory: true,
      llm_router: true,
      vector_store: true,
    },
  };

  return NextResponse.json(status);
}

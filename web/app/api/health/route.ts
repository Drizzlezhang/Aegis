import { NextResponse } from 'next/server';

export async function GET() {
  const startTime = Date.now();

  // Check backend connectivity
  let backendStatus = 'unknown';
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const res = await fetch(`${backendUrl}/api/status`, {
      signal: AbortSignal.timeout(5000),
    });
    backendStatus = res.ok ? 'connected' : 'error';
  } catch {
    backendStatus = 'unreachable';
  }

  const responseTime = Date.now() - startTime;

  const health = {
    status: backendStatus === 'connected' ? 'healthy' : 'degraded',
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '0.0.0',
    uptime: process.uptime(),
    responseTimeMs: responseTime,
    backend: backendStatus,
  };

  const statusCode = health.status === 'healthy' ? 200 : 503;
  return NextResponse.json(health, { status: statusCode });
}

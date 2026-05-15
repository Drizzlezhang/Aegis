import { NextResponse } from 'next/server';
import { getServerApiBase } from '@/utils/server-api-base';

export async function POST(request: Request) {
  try {
    const body = await request.text();
    const res = await fetch(`${getServerApiBase()}/api/analyze/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Backend error: ${res.status}` }));
      return NextResponse.json(err, { status: res.status });
    }

    return new Response(res.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to stream analysis' },
      { status: 500 }
    );
  }
}

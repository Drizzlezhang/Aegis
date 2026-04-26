import { NextResponse } from 'next/server';
import { getServerApiBase } from '@/utils/server-api-base';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${getServerApiBase()}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Backend error: ${res.status}` }));
      return NextResponse.json(err, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to run analysis' },
      { status: 500 }
    );
  }
}

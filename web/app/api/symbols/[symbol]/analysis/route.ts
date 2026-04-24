import { NextResponse } from 'next/server';

const API_BASE = process.env.API_BASE_URL || 'http://127.0.0.1:8001';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  try {
    const { symbol } = await params;
    const res = await fetch(`${API_BASE}/api/symbols/${encodeURIComponent(symbol)}/analysis`);
    if (!res.ok) {
      return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to fetch symbol analysis' },
      { status: 500 }
    );
  }
}

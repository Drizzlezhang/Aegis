import { NextResponse } from 'next/server';

const API_BASE = process.env.API_BASE_URL || 'http://127.0.0.1:8001';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const backendUrl = new URL(`${API_BASE}/api/analysis`);
    searchParams.forEach((value, key) => backendUrl.searchParams.set(key, value));

    const res = await fetch(backendUrl.toString());
    if (!res.ok) {
      return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to fetch analysis history' },
      { status: 500 }
    );
  }
}

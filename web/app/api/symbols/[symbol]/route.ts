import { NextResponse } from 'next/server';
import { getServerApiBase } from '@/utils/server-api-base';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ symbol: string }> }
) {
  try {
    const { symbol } = await params;
    const res = await fetch(`${getServerApiBase()}/api/symbols/${encodeURIComponent(symbol)}`);
    if (!res.ok) {
      return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to fetch symbol detail' },
      { status: 500 }
    );
  }
}

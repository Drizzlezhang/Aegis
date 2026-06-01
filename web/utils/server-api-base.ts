const LOCAL_DEV_FALLBACKS = new Set(['localhost', '127.0.0.1']);
const DEFAULT_SERVER_API_PORT = '8000';

function normalizeBase(value: string): string {
  return value.replace(/\/$/, '');
}

function getLocalDevFallbackFromRequestOrigin(): string | null {
  const origin = process.env.NEXT_PUBLIC_SITE_URL || process.env.SITE_URL;
  if (!origin) {
    return null;
  }

  try {
    const url = new URL(origin);
    if (!LOCAL_DEV_FALLBACKS.has(url.hostname)) {
      return null;
    }
    return `${url.protocol}//${url.hostname}:${DEFAULT_SERVER_API_PORT}`;
  } catch {
    return null;
  }
}

export function getServerApiBase(): string {
  const configured = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured) {
    return normalizeBase(configured);
  }

  const localFallback = getLocalDevFallbackFromRequestOrigin();
  if (localFallback) {
    return localFallback;
  }

  // Last resort: default to localhost:8000 for local dev
  return `http://localhost:${DEFAULT_SERVER_API_PORT}`;
}

const DEFAULT_SERVER_API_BASE = 'http://127.0.0.1:8003';

export function getServerApiBase(): string {
  const configured = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }
  return DEFAULT_SERVER_API_BASE;
}

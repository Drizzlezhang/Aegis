export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('aegis_token');
  localStorage.removeItem('aegis_token_expires');
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  const token = localStorage.getItem('aegis_token');
  const expires = localStorage.getItem('aegis_token_expires');
  if (!token || !expires) return null;
  if (Date.now() > Number(expires)) {
    clearToken();
    return null;
  }
  return token;
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

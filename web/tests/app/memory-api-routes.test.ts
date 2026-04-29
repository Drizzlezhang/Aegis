import { describe, expect, it } from 'vitest';

describe('api routes', () => {
  it('exposes memory stats route module', async () => {
    await expect(import('@/app/api/memory/stats/route')).resolves.toHaveProperty('GET');
  });

  it('exposes memory notes route module', async () => {
    await expect(import('@/app/api/memory/notes/route')).resolves.toHaveProperty('GET');
  });

  it('exposes memory search route module', async () => {
    await expect(import('@/app/api/memory/search/route')).resolves.toHaveProperty('POST');
  });

  it('exposes market indices route module', async () => {
    await expect(import('@/app/api/market/indices/route')).resolves.toHaveProperty('GET');
  });
});

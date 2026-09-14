import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => { vi.resetModules(); });
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); delete window.Telegram; });

function telegram() {
  window.Telegram = { WebApp: { initData: 'signed-telegram-data' } } as typeof window.Telegram;
}

describe('API authentication', () => {
  it('sends signed data and never sends a user ID', async () => {
    telegram();
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetcher);
    const { request } = await import('../src/api');
    await request('/user/stats');
    const options = fetcher.mock.calls[0][1];
    expect(options.headers['X-Telegram-Init-Data']).toBe('signed-telegram-data');
    expect(options.headers['X-Telegram-User-Id']).toBeUndefined();
    expect(options.credentials).toBe('omit');
  });

  it('does not make requests outside Telegram', async () => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    const { request } = await import('../src/api');
    await expect(request('/user/stats')).rejects.toThrow('Telegram');
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('explains expired sessions and does not display validation objects', async () => {
    telegram();
    const fetcher = vi.fn().mockResolvedValueOnce(new Response('{}', { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: [{ input: 'private value' }] }), { status: 422 }));
    vi.stubGlobal('fetch', fetcher);
    const { request } = await import('../src/api');
    await expect(request('/user/stats')).rejects.toThrow('Сессия истекла');
    await expect(request('/tobaccos')).rejects.toThrow('Не удалось выполнить запрос');
  });
});

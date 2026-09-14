import { request } from './api';

export type ShareKind = 'mix' | 'collection';
export type ShareLink = { id: string; token: string; expires_at: number };
export type OwnShare = { id: string; kind: ShareKind; title: string; created_at: number; expires_at: number };
export type SharedSnapshot = { kind: ShareKind; title: string; created_at: number; expires_at: number;
  tobaccos?: Array<{ name: string; brand: string | null }>;
  components?: Array<{ name: string; portion: number; role: string }>;
  description?: string | null; tips?: string | null };

export const shareUrl = (token: string) => `${window.location.origin}/#share=${encodeURIComponent(token)}`;
export const sharesApi = {
  create: (kind: ShareKind, mixId?: number) => request<ShareLink>('/shares', { method: 'POST', body: JSON.stringify({ kind, ...(kind === 'mix' ? { mix_id: mixId } : {}) }) }),
  list: () => request<OwnShare[]>('/shares'),
  revoke: (id: string) => request(`/shares/${id}`, { method: 'DELETE' }),
  open: async (token: string, signal: AbortSignal): Promise<SharedSnapshot> => {
    if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw new Error('Эта ссылка недействительна.');
    // Public requests never attach Telegram credentials, even inside Telegram.
    const controller = new AbortController();
    const abort = () => controller.abort();
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) abort();
    const timer = setTimeout(abort, 60000); // Free hosting may wake from sleep.
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/shares/open`, {
        method: 'POST', credentials: 'omit', referrerPolicy: 'no-referrer', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }),
      });
      if (!response.ok) {
        if (response.status === 404) throw new Error('Ссылка истекла или была отключена. Попросите друга прислать новую.');
        throw new Error('Не удалось открыть ссылку. Попробуйте чуть позже.');
      }
      return await response.json();
    } catch (error) {
      if (controller.signal.aborted) throw new Error('Загрузка заняла слишком много времени. Попробуйте ещё раз.');
      if (error instanceof TypeError) throw new Error('Проверьте подключение к интернету.');
      throw error;
    } finally { clearTimeout(timer); signal.removeEventListener('abort', abort); }
  },
};

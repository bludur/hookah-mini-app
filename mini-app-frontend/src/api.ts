import { tg } from './telegram';

// В production замените на URL вашего backend на Render
const API_BASE = import.meta.env.VITE_API_URL || '/api';

// Типы данных
export interface Category {
  id: number;
  name: string;
  emoji: string;
  taste_profile: string;
}

export interface Tobacco {
  id: number;
  user_id: number;
  name: string;
  brand: string | null;
  category_id: number | null;
  notes: string | null;
  created_at: string;
  category: Category | null;
}

export interface MixComponent {
  tobacco: string;
  portion: number;
  role: string;
}

export interface Mix {
  id: number;
  user_id: number;
  name: string;
  components: Record<string, { portion: number; role: string }>;
  description: string | null;
  tips: string | null;
  rating: number | null;
  is_favorite: boolean;
  request_type: string;
  created_at: string;
}

export interface MixGenerateResponse {
  id: number;
  name: string;
  components: MixComponent[];
  description: string;
  tips: string;
}

export interface Stats {
  tobaccos_count: number;
  mixes_count: number;
  favorites_count: number;
}

export interface BulkResult {
  added: string[];
  skipped: string[];
  errors: string[];
}

// Only signed Telegram data identifies the user. No production or development mock identity.
const getHeaders = (): Record<string, string> => {
  if (!tg?.initData) throw new Error('Откройте приложение из Telegram.');
  return { 'Content-Type': 'application/json', 'X-Telegram-Init-Data': tg.initData };
};

export async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = { ...options.headers, ...getHeaders() };
  const controller = new AbortController();
  const forwardAbort = () => controller.abort();
  if (options.signal?.aborted) controller.abort();
  options.signal?.addEventListener('abort', forwardAbort, { once: true });
  const timer = setTimeout(() => controller.abort(), ['/mixes/generate', '/tobaccos/recognize-photo'].includes(endpoint) ? 60000 : 15000);
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options, headers, credentials: 'omit', signal: controller.signal,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      if (response.status === 401) throw new Error('Сессия истекла. Закройте и откройте приложение заново в Telegram.');
      throw new Error(typeof error?.detail === 'string' ? error.detail : 'Не удалось выполнить запрос. Попробуйте ещё раз.');
    }
    return await response.json();
  } catch (error) {
    if (controller.signal.aborted) throw new Error('Превышено время ожидания. Обновите данные перед повторной попыткой.');
    if (error instanceof TypeError) throw new Error('Не удалось связаться с сервером. Проверьте подключение.');
    throw error;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', forwardAbort);
  }
}

// ============ USER API ============

export const userApi = {
  getStats: () => request<Stats>('/user/stats'),
};

// ============ CATEGORIES API ============

export const categoriesApi = {
  getAll: () => request<Category[]>('/categories'),
};

// ============ TOBACCOS API ============

export const tobaccosApi = {
  recognizePhoto: (image: string) => request<{ tobaccos: Array<{ name: string; brand: string | null }>; unreadable: boolean }>('/tobaccos/recognize-photo', {
    method: 'POST', body: JSON.stringify({ image }),
  }),
  getAll: () => request<Tobacco[]>('/tobaccos'),
  
  getById: (id: number) => request<Tobacco>(`/tobaccos/${id}`),
  
  create: (data: { name: string; brand?: string; category_id?: number }) =>
    request<Tobacco>('/tobaccos', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  createBulk: (tobaccos: Array<{ name: string; brand?: string; category_id?: number }>) =>
    request<BulkResult>('/tobaccos/bulk', {
      method: 'POST',
      body: JSON.stringify({ tobaccos }),
    }),
  
  update: (id: number, data: { name?: string; brand?: string | null; category_id?: number | null; notes?: string | null }) =>
    request<Tobacco>(`/tobaccos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: number) =>
    request<{ message: string }>(`/tobaccos/${id}`, {
      method: 'DELETE',
    }),
  
  deleteAll: () =>
    request<{ message: string }>('/tobaccos', {
      method: 'DELETE',
    }),
};

// ============ MIXES API ============

export const mixesApi = {
  generate: (data: {
    request_type: 'base' | 'profile' | 'surprise';
    base_tobacco?: string;
    base_tobacco_id?: number;
    taste_profile?: string;
  }) =>
    request<MixGenerateResponse>('/mixes/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  getAll: (limit = 20, offset = 0) => request<Mix[]>(`/mixes?limit=${limit}&offset=${offset}`),
  
  getFavorites: (limit = 20, offset = 0) => request<Mix[]>(`/mixes/favorites?limit=${limit}&offset=${offset}`),
  
  getById: (id: number) => request<Mix>(`/mixes/${id}`),
  
  rate: (id: number, rating: number) =>
    request<Mix>(`/mixes/${id}/rate`, {
      method: 'POST',
      body: JSON.stringify({ rating }),
    }),
  
  toggleFavorite: (id: number, is_favorite: boolean) =>
    request<Mix>(`/mixes/${id}/favorite`, {
      method: 'POST',
      body: JSON.stringify({ is_favorite }),
    }),
  
  clearFavorites: () =>
    request<{ message: string }>('/mixes/favorites', {
      method: 'DELETE',
    }),
};

import { getTelegramUser, getMockUser, isTelegramWebApp } from './telegram';

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

// Получение заголовков с данными пользователя
const getHeaders = (): Record<string, string> => {
  const user = isTelegramWebApp() ? getTelegramUser() : getMockUser();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (user) {
    headers['X-Telegram-User-Id'] = String(user.id);
    if (user.username) headers['X-Telegram-Username'] = encodeURIComponent(user.username);
    if (user.first_name) headers['X-Telegram-First-Name'] = encodeURIComponent(user.first_name);
  }
  
  return headers;
};

// Базовая функция запроса
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Ошибка сети' }));
    throw new Error(error.detail || 'Произошла ошибка');
  }

  return response.json();
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
  
  update: (id: number, data: { name?: string; brand?: string; category_id?: number }) =>
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
    taste_profile?: string;
  }) =>
    request<MixGenerateResponse>('/mixes/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  getAll: (limit = 20) => request<Mix[]>(`/mixes?limit=${limit}`),
  
  getFavorites: () => request<Mix[]>('/mixes/favorites'),
  
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

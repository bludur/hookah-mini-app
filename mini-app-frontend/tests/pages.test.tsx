import { beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CollectionPage } from '../src/pages/CollectionPage';
import { HistoryPage } from '../src/pages/HistoryPage';
import { Modal } from '../src/components/Modal';
import { useStore } from '../src/store';
import { tobaccosApi, categoriesApi, mixesApi } from '../src/api';

vi.mock('../src/api', () => ({
  tobaccosApi: { getAll: vi.fn(), create: vi.fn(), update: vi.fn() },
  categoriesApi: { getAll: vi.fn() },
  mixesApi: { getAll: vi.fn() },
}));
vi.mock('../src/telegram', () => ({ hapticFeedback: { light: vi.fn(), success: vi.fn(), error: vi.fn(), selection: vi.fn() }, showConfirm: vi.fn() }));

beforeEach(() => { vi.clearAllMocks(); useStore.setState({ tobaccos: [], categories: [], mixes: [] }); });

it('shows load errors and retries instead of claiming an empty collection', async () => {
  vi.mocked(tobaccosApi.getAll).mockRejectedValueOnce(new Error('Сервер недоступен')).mockResolvedValue([]);
  vi.mocked(categoriesApi.getAll).mockResolvedValue([]);
  render(<CollectionPage />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Сервер недоступен');
  expect(screen.queryByText('Коллекция пуста')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }));
  expect(await screen.findByText('Коллекция пуста')).toBeInTheDocument();
});

it('loads older history pages', async () => {
  const row = (id: number) => ({ id, user_id: 1, name: `Recipe ${id}`, components: {}, description: null, tips: null, rating: null, is_favorite: false, request_type: 'surprise', created_at: '2026-01-01T00:00:00+00:00' });
  vi.mocked(mixesApi.getAll).mockResolvedValueOnce(Array.from({ length: 20 }, (_, i) => row(i)))
    .mockResolvedValueOnce([row(20)]);
  render(<HistoryPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Загрузить ещё' }));
  expect(await screen.findByText(/Recipe 20/)).toBeInTheDocument();
  expect(mixesApi.getAll).toHaveBeenLastCalledWith(20, 20);
});

it('uses an accessible scrollable dialog and restores body scrolling', async () => {
  const close = vi.fn();
  const view = render(<Modal isOpen title="Рецепт" onClose={close}><p>Long recipe</p></Modal>);
  const dialog = screen.getByRole('dialog', { name: 'Рецепт' });
  expect(dialog).toHaveAttribute('open');
  expect(document.body.style.overflow).toBe('hidden');
  expect(screen.getByText('Long recipe').parentElement).toHaveClass('overflow-y-auto');
  fireEvent.click(screen.getByRole('button', { name: 'Закрыть' }));
  expect(close).toHaveBeenCalled();
  view.unmount();
  expect(document.body.style.overflow).toBe('');
});

it('edits a tobacco and sends explicit null to clear optional fields', async () => {
  const item = { id: 7, user_id: 1, name: 'Mango', brand: 'Brand', category_id: 1,
    category: { id: 1, name: 'Fruit', emoji: 'F', taste_profile: 'sweet' }, notes: null,
    created_at: '2026-01-01T00:00:00+00:00' };
  vi.mocked(tobaccosApi.getAll).mockResolvedValue([item]);
  vi.mocked(categoriesApi.getAll).mockResolvedValue([item.category]);
  vi.mocked(tobaccosApi.update).mockResolvedValue({ ...item, name: 'Mint', brand: null, category_id: null, category: null });
  render(<CollectionPage />);
  fireEvent.click(await screen.findByText('Mango'));
  fireEvent.click(screen.getByRole('button', { name: 'Изменить' }));
  fireEvent.change(screen.getByLabelText('Название'), { target: { value: 'Mint' } });
  fireEvent.change(screen.getByLabelText('Бренд'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Категория'), { target: { value: '' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }));
  await waitFor(() => expect(tobaccosApi.update).toHaveBeenCalledWith(7, { name: 'Mint', brand: null, category_id: null }));
  expect(await screen.findByText('Mint')).toBeInTheDocument();
});

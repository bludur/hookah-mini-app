import { beforeEach, expect, it, vi } from 'vitest';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { ShareButton } from '../src/components/ShareButton';
import { SharedPage } from '../src/pages/SharedPage';
import { sharesApi } from '../src/sharing';

vi.mock('../src/sharing', async importOriginal => {
  const actual = await importOriginal<typeof import('../src/sharing')>();
  return { ...actual, sharesApi: { create: vi.fn(), list: vi.fn(), revoke: vi.fn(), open: vi.fn() } };
});
vi.mock('../src/telegram', () => ({ hapticFeedback: { light: vi.fn() } }));
beforeEach(() => { vi.clearAllMocks(); vi.mocked(sharesApi.list).mockResolvedValue([]); });

it('creates a link only after explicit action and revokes the generated link', async () => {
  const link={ id:'a'.repeat(64), token:'x'.repeat(43), expires_at:2000000000 };
  vi.mocked(sharesApi.create).mockResolvedValue(link);
  render(<ShareButton kind="mix" mixId={7} />);
  fireEvent.click(screen.getByRole('button',{name:'Поделиться миксом'}));
  expect(sharesApi.create).not.toHaveBeenCalled();
  vi.mocked(sharesApi.list).mockResolvedValue([{...link,kind:'mix',title:'Test mix',created_at:1900000000}]);
  fireEvent.click(screen.getByRole('button',{name:'Создать ссылку'}));
  expect((await screen.findByLabelText('Ссылка для друга') as HTMLInputElement).value).toContain('/#share=');
  expect(sharesApi.create).toHaveBeenCalledWith('mix',7);
  fireEvent.click(screen.getByText(/Мои активные ссылки/));
  fireEvent.click(await screen.findByRole('button',{name:'Отключить ссылку'}));
  await waitFor(()=>expect(sharesApi.revoke).toHaveBeenCalledWith(link.id));
  expect(await screen.findByText('Ссылка отключена.')).toBeInTheDocument();
});

it('renders a shared list without private navigation and escapes labels', async () => {
  vi.mocked(sharesApi.open).mockResolvedValue({kind:'collection',title:'List',created_at:1900000000,expires_at:2000000000,tobaccos:[{name:'<script>alert(1)</script>',brand:'Brand'}]});
  render(<SharedPage token={'x'.repeat(43)} />);
  expect(await screen.findByText('<script>alert(1)</script>')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
});

it('explains expired links and permits retry', async () => {
  vi.mocked(sharesApi.open).mockRejectedValue(new Error('Ссылка истекла'));
  render(<SharedPage token={'x'.repeat(43)} />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Ссылка истекла');
  fireEvent.click(screen.getByRole('button',{name:'Попробовать снова'}));
  await waitFor(()=>expect(sharesApi.open).toHaveBeenCalledTimes(2));
});

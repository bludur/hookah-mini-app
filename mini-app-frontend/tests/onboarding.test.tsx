import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Onboarding, completeOnboarding, needsOnboarding } from '../src/components/Onboarding';
import { getTelegramUser } from '../src/telegram';

vi.mock('../src/telegram', () => ({ getTelegramUser: vi.fn(), hapticFeedback: { light: vi.fn() } }));
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

it('supports forward, back, and a deliberate start action', () => {
  const onStart = vi.fn();
  render(<Onboarding onClose={vi.fn()} onStart={onStart} />);
  expect(screen.getByRole('button', { name: 'Назад' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Далее' }));
  expect(screen.getByText('Найдите своё сочетание')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Назад' }));
  expect(screen.getByText('Начните со своей коллекции')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Далее' }));
  fireEvent.click(screen.getByRole('button', { name: 'Далее' }));
  expect(onStart).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Добавить первые табаки' }));
  expect(onStart).toHaveBeenCalledOnce();
});

it('allows skipping immediately and closing with Escape', () => {
  const onClose = vi.fn();
  render(<Onboarding onClose={onClose} onStart={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Пропустить' }));
  expect(onClose).toHaveBeenCalledOnce();
  fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }));
  expect(onClose).toHaveBeenCalledTimes(2);
});

it('remembers completion separately for each user', () => {
  vi.mocked(getTelegramUser).mockReturnValue({ id: 901, first_name: 'A' });
  expect(needsOnboarding()).toBe(true);
  completeOnboarding();
  expect(localStorage.getItem('hookah:onboarding:v1:901')).toBe('done');
  expect(needsOnboarding()).toBe(false);
  vi.mocked(getTelegramUser).mockReturnValue({ id: 902, first_name: 'B' });
  expect(needsOnboarding()).toBe(true);
  localStorage.setItem('hookah:onboarding:v1:902', 'done');
  expect(needsOnboarding()).toBe(false);
});

it('remains usable when device storage is blocked', () => {
  vi.mocked(getTelegramUser).mockReturnValue({ id: 903, first_name: 'C' });
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked'); });
  expect(needsOnboarding()).toBe(true);
  expect(() => completeOnboarding()).not.toThrow();
  expect(needsOnboarding()).toBe(false);
});

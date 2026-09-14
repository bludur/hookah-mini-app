import { beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PhotoImport } from '../src/components/PhotoImport';
import { tobaccosApi } from '../src/api';
import { preparePhoto } from '../src/photo';

vi.mock('../src/api', () => ({ tobaccosApi: { recognizePhoto: vi.fn(), createBulk: vi.fn() } }));
vi.mock('../src/photo', () => ({ preparePhoto: vi.fn() }));
vi.mock('../src/telegram', () => ({ hapticFeedback: { light: vi.fn() } }));
beforeEach(() => { vi.clearAllMocks(); vi.mocked(preparePhoto).mockResolvedValue('encoded-photo'); });

async function selectPhoto() {
  fireEvent.click(screen.getByRole('button', { name: 'Добавить по фото' }));
  fireEvent.change(screen.getByLabelText('Выбрать фото пачек'), { target: { files: [new File(['jpeg'], 'photo.jpg', { type: 'image/jpeg' })] } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Распознать' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: 'Распознать' }));
}

it('requires review, accepts edits and excludes removed products before saving', async () => {
  vi.mocked(tobaccosApi.recognizePhoto).mockResolvedValue({ tobaccos: [{ name: 'Mango', brand: 'A' }, { name: 'Mint', brand: 'B' }], unreadable: true });
  vi.mocked(tobaccosApi.createBulk).mockResolvedValue({ added: ['Corrected Mango'], skipped: [], errors: [] });
  const onAdded = vi.fn(); render(<PhotoImport onAdded={onAdded} />);
  await selectPhoto();
  expect(await screen.findByLabelText('Название 1')).toHaveValue('Mango');
  expect(tobaccosApi.createBulk).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Название 1'), { target: { value: 'Corrected Mango' } });
  fireEvent.click(screen.getByRole('button', { name: 'Убрать строку 2' }));
  fireEvent.click(screen.getByRole('button', { name: 'Добавить всё (1)' }));
  await waitFor(() => expect(tobaccosApi.createBulk).toHaveBeenCalledWith([{ name: 'Corrected Mango', brand: 'A' }]));
  expect(onAdded).toHaveBeenCalledOnce();
  expect(await screen.findByRole('status')).toHaveTextContent('Добавлено: 1');
});

it('shows provider failure without adding anything or losing the photo', async () => {
  vi.mocked(tobaccosApi.recognizePhoto).mockRejectedValue(new Error('Лимит распознаваний исчерпан'));
  render(<PhotoImport onAdded={vi.fn()} />); await selectPhoto();
  expect(await screen.findByRole('alert')).toHaveTextContent('Лимит распознаваний исчерпан');
  expect(screen.getByAltText('Выбранное фото пачек')).toBeInTheDocument();
  expect(tobaccosApi.createBulk).not.toHaveBeenCalled();
});

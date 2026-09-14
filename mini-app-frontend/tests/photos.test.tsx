import { beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PhotoImport } from '../src/components/PhotoImport';
import { tobaccosApi } from '../src/api';
import { preparePhoto } from '../src/photo';
import { readPhotoLocally } from '../src/localOcr';

vi.mock('../src/api', () => ({ tobaccosApi: { recognizePhoto: vi.fn(), createBulk: vi.fn() } }));
vi.mock('../src/photo', () => ({ preparePhoto: vi.fn() }));
vi.mock('../src/localOcr', () => ({ readPhotoLocally: vi.fn() }));
vi.mock('../src/telegram', () => ({ hapticFeedback: { light: vi.fn() } }));
beforeEach(() => { vi.clearAllMocks(); vi.mocked(preparePhoto).mockResolvedValue('encoded-photo'); });

async function selectPhoto(mode: 'local' | 'ai' = 'ai') {
  fireEvent.click(screen.getByRole('button', { name: 'Добавить по фото' }));
  fireEvent.change(screen.getByLabelText('Выбрать фото пачек'), { target: { files: [new File(['jpeg'], 'photo.jpg', { type: 'image/jpeg' })] } });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Прочитать на устройстве' })).toBeEnabled());
  if (mode === 'ai') fireEvent.click(screen.getByText('Сложный снимок? Помощь AI'));
  fireEvent.click(screen.getByRole('button', { name: mode === 'local' ? 'Прочитать на устройстве' : 'Распознать через AI' }));
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

it('reads locally repeatedly without calling cloud or saving before confirmation', async () => {
  vi.mocked(readPhotoLocally).mockResolvedValue('DARKSIDE\nMANGO\nTOBACCO\n100 g');
  render(<PhotoImport onAdded={vi.fn()} />);
  await selectPhoto('local');
  expect(await screen.findByLabelText('Название 1')).toHaveValue('MANGO');
  expect(screen.getByLabelText('Бренд 1')).toHaveValue('Darkside');
  for (let attempt = 0; attempt < 4; attempt++) {
    fireEvent.click(screen.getByRole('button', { name: 'Другое фото' }));
    fireEvent.change(screen.getByLabelText('Выбрать фото пачек'), { target: { files: [new File(['jpeg'], 'p.jpg', { type: 'image/jpeg' })] } });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Прочитать на устройстве' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Прочитать на устройстве' }));
    await screen.findByLabelText('Название 1');
  }
  expect(readPhotoLocally).toHaveBeenCalledTimes(5);
  expect(tobaccosApi.recognizePhoto).not.toHaveBeenCalled();
  expect(tobaccosApi.createBulk).not.toHaveBeenCalled();
});

it('local failure never automatically uploads the photo and permits manual entry', async () => {
  vi.mocked(readPhotoLocally).mockRejectedValue(new Error('Не удалось прочитать'));
  render(<PhotoImport onAdded={vi.fn()} />); await selectPhoto('local');
  expect(await screen.findByRole('alert')).toHaveTextContent('Не удалось прочитать');
  expect(tobaccosApi.recognizePhoto).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Ввести вручную' }));
  expect(screen.getByLabelText('Название 1')).toHaveValue('');
});

it('unmount aborts local recognition', async () => {
  vi.mocked(readPhotoLocally).mockImplementation(() => new Promise(() => {}));
  const view = render(<PhotoImport onAdded={vi.fn()} />); await selectPhoto('local');
  const signal = vi.mocked(readPhotoLocally).mock.calls[0][1];
  view.unmount(); expect(signal.aborted).toBe(true);
});

it('shows provider failure without adding anything or losing the photo', async () => {
  vi.mocked(tobaccosApi.recognizePhoto).mockRejectedValue(new Error('Лимит распознаваний исчерпан'));
  render(<PhotoImport onAdded={vi.fn()} />); await selectPhoto();
  expect(await screen.findByRole('alert')).toHaveTextContent('Лимит распознаваний исчерпан');
  expect(screen.getByAltText('Выбранное фото пачек')).toBeInTheDocument();
  expect(tobaccosApi.createBulk).not.toHaveBeenCalled();
});

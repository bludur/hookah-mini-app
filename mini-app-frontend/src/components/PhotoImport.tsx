import { useEffect, useRef, useState } from 'react';
import { Camera, ImagePlus, Trash2, ScanLine } from 'lucide-react';
import { tobaccosApi } from '../api';
import { preparePhoto } from '../photo';
import { readPhotoLocally } from '../localOcr';
import { matchLabel, type CatalogEntry } from '../labelMatcher';
import { Modal } from './Modal';
import { Button } from './Button';
import { Input } from './Input';

type Draft = { name: string; brand: string };

export function PhotoImport({ onAdded, catalog = [] }: { onAdded: () => void; catalog?: CatalogEntry[] }) {
  const [open, setOpen] = useState(false);
  const [image, setImage] = useState('');
  const [rows, setRows] = useState<Draft[] | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [localText, setLocalText] = useState('');
  const [candidates, setCandidates] = useState<string[]>([]);
  const [progress, setProgress] = useState('');
  const localJob = useRef<AbortController | null>(null);
  const alive = useRef(true);
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; localJob.current?.abort(); }; }, []);

  const choose = async (file?: File) => {
    if (!file || busy) return;
    setBusy(true); setError(''); setRows(null); setImage(''); setLocalText(''); setCandidates([]); setProgress('Открываем фото…');
    try {
      const prepared = await preparePhoto(file);
      if (alive.current) setImage(prepared);
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Не удалось открыть фото.');
    } finally { if (alive.current) setBusy(false); }
  };
  const recognizeLocal = async () => {
    if (busy || !image) return;
    const controller = new AbortController(); localJob.current = controller;
    setBusy(true); setError(''); setProgress('Подготавливаем распознавание…');
    try {
      const text = await readPhotoLocally(image, controller.signal, value => { if (alive.current) setProgress(value); });
      if (!alive.current || controller.signal.aborted) return;
      const result = matchLabel(text, catalog);
      setLocalText(text); setCandidates(result.candidates); setRows([result.draft]);
      setUnreadable(!result.draft.name);
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Не удалось прочитать фото.');
    } finally { localJob.current = null; if (alive.current) setBusy(false); }
  };
  const recognize = async () => {
    if (busy || !image) return;
    setBusy(true); setError(''); setProgress('Распознаём фото…');
    try {
      const result = await tobaccosApi.recognizePhoto(image);
      if (!alive.current) return;
      setRows(result.tobaccos.map(t => ({ name: t.name, brand: t.brand || '' })));
      setUnreadable(result.unreadable);
      setLocalText(''); setCandidates([]);
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Не удалось распознать фото.');
    } finally { if (alive.current) setBusy(false); }
  };
  const save = async () => {
    if (!rows?.length) return;
    setBusy(true); setError(''); setProgress('Сохраняем…');
    try {
      const result = await tobaccosApi.createBulk(rows.map(r => ({ name: r.name.trim(), brand: r.brand.trim() || undefined })));
      if (!alive.current) return;
      setNotice(`Добавлено: ${result.added.length}. Уже в коллекции: ${result.skipped.length}.`);
      if (result.errors.length) setError(result.errors.join('. '));
      else { setOpen(false); setImage(''); setRows(null); }
      onAdded();
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Не удалось сохранить список.');
    } finally { if (alive.current) setBusy(false); }
  };
  const edit = (index: number, field: keyof Draft, value: string) =>
    setRows(previous => previous?.map((r, i) => i === index ? { ...r, [field]: value } : r) || []);

  return <>
    <Button variant="secondary" size="sm" icon={<Camera className="w-4 h-4" />} onClick={() => {
      setOpen(true); setError(''); setNotice('');
    }}>Добавить по фото</Button>
    {notice && <p role="status" className="text-sm text-tg-hint w-full">{notice}</p>}
    <Modal isOpen={open} title="Добавить по фото" onClose={() => {
      if (!busy) { setOpen(false); setImage(''); setRows(null); setError(''); setLocalText(''); setCandidates([]); }
    }}>
      <div className="space-y-3">
        <div className="photo-step"><span data-active={rows === null}>01 · Фото</span><span aria-hidden="true">—</span><span data-active={rows !== null}>02 · Проверка</span></div>
        {!image && rows === null && <div className="photo-intro"><div className="icon-tile"><ScanLine className="w-6 h-6" /></div><h3 className="font-semibold mb-2">Наведите камеру на пачку</h3><p className="text-sm text-tg-hint">Название должно быть видно целиком.<br />Без бликов — получится точнее.</p></div>}
        <input ref={camera} aria-label="Снять пачки" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; void choose(file); }} />
        <input ref={gallery} aria-label="Выбрать фото пачек" type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; void choose(file); }} />
        <div className="grid grid-cols-2 gap-2">
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => camera.current?.click()} icon={<Camera className="w-4 h-4" />}>Камера</Button>
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => gallery.current?.click()} icon={<ImagePlus className="w-4 h-4" />}>Галерея</Button>
        </div>
        {image && <img src={`data:image/jpeg;base64,${image}`} alt="Выбранное фото пачек" className="photo-preview" />}
        {rows === null && <>
          <p className="text-xs text-tg-hint">Фото остаётся на вашем устройстве.</p>
          <Button fullWidth disabled={!image || busy} loading={busy} icon={<ScanLine className="w-4 h-4" />} onClick={recognizeLocal}>Прочитать на устройстве</Button>
          <Button fullWidth variant="ghost" disabled={busy} onClick={() => { setRows([{ name: '', brand: '' }]); setUnreadable(false); }}>Ввести вручную</Button>
        </>}
        {rows !== null && <>
          <p className="text-sm">Всё верно? При необходимости исправьте название и бренд.</p>
          {(unreadable || !rows.length) && <p role="status" className="text-sm text-tg-hint">Не удалось определить название. Впишите его или выберите из прочитанного текста.</p>}
          {localText && <details><summary className="text-sm cursor-pointer">Текст с упаковки</summary>
            <p className="text-xs text-tg-hint">Выберите нужную строку или впишите название самостоятельно.</p>
            <pre className="text-xs whitespace-pre-wrap break-words max-h-40 overflow-auto">{localText}</pre>
          </details>}
          {rows.map((row, index) => <div key={index} className="space-y-2 p-3 bg-tg-secondary-bg rounded-xl">
            <Input label="Название вкуса" aria-label={`Название ${index + 1}`} value={row.name} maxLength={100} disabled={busy} onChange={e => edit(index, 'name', e.target.value)} />
            {index === 0 && candidates.length > 0 && <select aria-label="Выбрать название из текста" className="w-full p-2 rounded bg-tg-secondary-bg text-tg-text" value="" disabled={busy} onChange={e => { if (e.target.value) edit(index, 'name', e.target.value); }}>
              <option value="">Выбрать название из текста</option>
              {candidates.map(candidate => <option key={candidate} value={candidate}>{candidate}</option>)}
            </select>}
            <Input label="Бренд" aria-label={`Бренд ${index + 1}`} placeholder="Необязательно" value={row.brand} maxLength={100} disabled={busy} onChange={e => edit(index, 'brand', e.target.value)} />
            <Button size="sm" variant="ghost" aria-label={`Убрать строку ${index + 1}`} disabled={busy} onClick={() => setRows(rows.filter((_, i) => i !== index))} icon={<Trash2 className="w-4 h-4" />}>Убрать</Button>
          </div>)}
          <Button fullWidth loading={busy} disabled={busy || !rows.length || rows.some(r => r.name.trim().length < 2)} onClick={save}>Добавить в коллекцию ({rows.length})</Button>
          <Button fullWidth variant="secondary" disabled={busy} onClick={() => { setRows(null); setImage(''); setError(''); setLocalText(''); setCandidates([]); }}>Другое фото</Button>
        </>}
        {image && <details className="ai-option"><summary>Сложный снимок? Помощь AI</summary>
          <p className="text-xs text-tg-hint my-2">Для сложной этикетки или нескольких пачек. Фото будет отправлено в OpenRouter для распознавания. Результат заменит текущий список.</p>
          <Button fullWidth variant="secondary" disabled={busy} onClick={recognize}>Распознать через AI</Button>
        </details>}
        {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
        {busy && <p role="status" className="text-sm text-tg-hint">{progress}</p>}
        {busy && localJob.current && <Button fullWidth variant="secondary" onClick={() => localJob.current?.abort()}>Отменить чтение</Button>}
      </div>
    </Modal>
  </>;
}

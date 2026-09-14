import { useEffect, useRef, useState } from 'react';
import { Camera, ImagePlus, Trash2 } from 'lucide-react';
import { tobaccosApi } from '../api';
import { preparePhoto } from '../photo';
import { Modal } from './Modal';
import { Button } from './Button';
import { Input } from './Input';

type Draft = { name: string; brand: string };

export function PhotoImport({ onAdded }: { onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [image, setImage] = useState('');
  const [rows, setRows] = useState<Draft[] | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const alive = useRef(true);
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  const choose = async (file?: File) => {
    if (!file || busy) return;
    setBusy(true); setError(''); setRows(null); setImage('');
    try {
      const prepared = await preparePhoto(file);
      if (alive.current) setImage(prepared);
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Не удалось открыть фото.');
    } finally { if (alive.current) setBusy(false); }
  };
  const recognize = async () => {
    setBusy(true); setError('');
    try {
      const result = await tobaccosApi.recognizePhoto(image);
      if (!alive.current) return;
      setRows(result.tobaccos.map(t => ({ name: t.name, brand: t.brand || '' })));
      setUnreadable(result.unreadable);
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Не удалось распознать фото.');
    } finally { if (alive.current) setBusy(false); }
  };
  const save = async () => {
    if (!rows?.length) return;
    setBusy(true); setError('');
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
    <Modal isOpen={open} title="Табаки по фото" onClose={() => {
      if (!busy) { setOpen(false); setImage(''); setRows(null); setError(''); }
    }}>
      <div className="space-y-3">
        <p className="text-sm text-tg-hint">Снимите до 5 пачек названиями к камере. Избегайте бликов и перекрытых надписей.</p>
        <input ref={camera} aria-label="Снять пачки" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden" onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; void choose(file); }} />
        <input ref={gallery} aria-label="Выбрать фото пачек" type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; void choose(file); }} />
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => camera.current?.click()} icon={<Camera className="w-4 h-4" />}>Камера</Button>
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => gallery.current?.click()} icon={<ImagePlus className="w-4 h-4" />}>Галерея</Button>
        </div>
        {image && <img src={`data:image/jpeg;base64,${image}`} alt="Выбранное фото пачек" className="w-full max-h-48 object-contain rounded-xl" />}
        {rows === null && <>
          <p className="text-xs text-tg-hint">Нажимая «Распознать», вы отправляете фото в OpenRouter и модель распознавания. Наш сервис не сохраняет снимок. Бесплатно, до 3 распознаваний в сутки; действует общий лимит сервиса.</p>
          <Button fullWidth disabled={!image || busy} loading={busy} onClick={recognize}>Распознать</Button>
        </>}
        {rows !== null && <>
          <p className="text-sm">Проверьте названия и бренды. В коллекцию попадут только строки, которые вы подтвердите.</p>
          {(unreadable || !rows.length) && <p role="status" className="text-sm text-tg-hint">Не всё удалось прочитать. Проверьте список или снимите нераспознанные пачки ближе.</p>}
          {rows.map((row, index) => <div key={index} className="space-y-2 p-3 bg-tg-secondary-bg rounded-xl">
            <Input aria-label={`Название ${index + 1}`} value={row.name} maxLength={100} disabled={busy} onChange={e => edit(index, 'name', e.target.value)} />
            <Input aria-label={`Бренд ${index + 1}`} placeholder="Бренд (если читается)" value={row.brand} maxLength={100} disabled={busy} onChange={e => edit(index, 'brand', e.target.value)} />
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => setRows(rows.filter((_, i) => i !== index))} icon={<Trash2 className="w-4 h-4" />}>Убрать строку {index + 1}</Button>
          </div>)}
          <Button fullWidth loading={busy} disabled={busy || !rows.length || rows.some(r => r.name.trim().length < 2)} onClick={save}>Добавить всё ({rows.length})</Button>
          <Button fullWidth variant="secondary" disabled={busy} onClick={() => { setRows(null); setImage(''); setError(''); }}>Другое фото</Button>
        </>}
        {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
        {busy && <p role="status" className="text-sm text-tg-hint">Обрабатываем… Бесплатная модель может отвечать до минуты.</p>}
      </div>
    </Modal>
  </>;
}

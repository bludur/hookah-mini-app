import { useEffect, useState } from 'react';
import { Copy, Share2, Link2 } from 'lucide-react';
import { sharesApi, shareUrl, type ShareKind, type ShareLink, type OwnShare } from '../sharing';
import { Button } from './Button';
import { Input } from './Input';
import { Modal } from './Modal';

export function ShareButton({ kind, mixId }: { kind: ShareKind; mixId?: number }) {
  const [open, setOpen] = useState(false);
  const [link, setLink] = useState<ShareLink | null>(null);
  const [links, setLinks] = useState<OwnShare[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  useEffect(() => { setLink(null); setError(''); setNotice(''); }, [kind, mixId]);
  useEffect(() => {
    if (!open) return;
    if (link && link.expires_at * 1000 <= Date.now()) setLink(null);
    let active = true;
    sharesApi.list().then(items => { if (active) setLinks(items); }).catch(() => { if (active) setError('Не удалось загрузить ваши ссылки.'); });
    return () => { active = false; };
  }, [open]);
  const create = async () => {
    setBusy(true); setError(''); setNotice('');
    try {
      const created = await sharesApi.create(kind, mixId); setLink(created);
      try { setLinks(await sharesApi.list()); }
      catch { setError('Ссылка готова, но список активных ссылок не обновился. Откройте окно ещё раз.'); }
    } catch (e) { setError(e instanceof Error ? e.message : 'Не удалось создать ссылку.'); }
    finally { setBusy(false); }
  };
  const revoke = async (id: string) => {
    setBusy(true); setError('');
    try { await sharesApi.revoke(id); setLinks(items => items.filter(item => item.id !== id)); if (link?.id === id) setLink(null); setNotice('Ссылка отключена.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Не удалось отключить ссылку.'); }
    finally { setBusy(false); }
  };
  const copy = async () => {
    if (!link) return;
    try { await navigator.clipboard.writeText(shareUrl(link.token)); setNotice('Ссылка скопирована. Отправьте её другу.'); }
    catch { setNotice('Выделите и скопируйте ссылку из поля ниже.'); }
  };
  const share = async () => {
    if (!link) return;
    if (!navigator.share) { await copy(); return; }
    try { await navigator.share({ title: kind === 'mix' ? 'Микс для тебя' : 'Мой список табаков', url: shareUrl(link.token) }); }
    catch (e) { if (!(e instanceof Error && e.name === 'AbortError')) setNotice('Не удалось открыть отправку. Скопируйте ссылку.'); }
  };
  return <>
    <Button variant="secondary" size="sm" icon={<Share2 className="w-4 h-4" />} onClick={() => { setOpen(true); setError(''); setNotice(''); }}>Поделиться {kind === 'mix' ? 'миксом' : 'списком'}</Button>
    <Modal isOpen={open} onClose={() => { if (!busy) setOpen(false); }} title="Поделиться с друзьями">
      <div className="space-y-4">
        <div className="icon-tile"><Link2 className="w-5 h-5" /></div>
        <p className="text-sm">{kind === 'mix' ? 'Друг увидит состав, пропорции, описание и совет к этому миксу.' : 'Друг увидит названия и бренды табаков в вашей коллекции на момент создания ссылки.'}</p>
        <p className="text-sm text-tg-hint">Просмотр доступен всем, у кого есть ссылка, в течение 7 дней. Профиль и личные заметки останутся скрыты. Ссылку можно отключить.</p>
        {!link ? <Button fullWidth loading={busy} onClick={create}>Создать ссылку</Button> : <>
          <Input label="Ссылка для друга" value={shareUrl(link.token)} readOnly onFocus={e => e.currentTarget.select()} />
          <div className="grid grid-cols-2 gap-2"><Button disabled={busy} icon={<Share2 className="w-4 h-4" />} onClick={share}>Отправить</Button><Button disabled={busy} variant="secondary" icon={<Copy className="w-4 h-4" />} onClick={copy}>Копировать</Button></div>
          <p className="text-xs text-tg-hint">До {new Date(link.expires_at * 1000).toLocaleDateString('ru-RU')}. Изменения оригинала не обновляют эту ссылку.</p>
        </>}
        {notice && <p role="status" className="text-sm text-tg-link">{notice}</p>}
        {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
        <details className="ai-option"><summary>Мои активные ссылки ({links.length})</summary>
          <div className="space-y-3 mt-3">{links.map(item => <div key={item.id} className="p-3 rounded-xl bg-tg-secondary-bg">
            <p className="text-sm font-medium break-words">{item.title}</p>
            <p className="text-xs text-tg-hint mt-1">Создана {new Date(item.created_at * 1000).toLocaleString('ru-RU')} · до {new Date(item.expires_at * 1000).toLocaleDateString('ru-RU')}</p>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => revoke(item.id)}>Отключить ссылку</Button>
          </div>)}{!links.length && <p className="text-sm text-tg-hint">Активных ссылок пока нет.</p>}</div>
        </details>
      </div>
    </Modal>
  </>;
}

import { useEffect, useState } from 'react';
import { Leaf, Package } from 'lucide-react';
import { sharesApi, type SharedSnapshot } from '../sharing';
import { Card } from '../components/Card';
import { Button } from '../components/Button';

export function SharedPage({ token }: { token: string }) {
  const [data, setData] = useState<SharedSnapshot | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setData(null); setError('');
    sharesApi.open(token, controller.signal).then(result => { if (!controller.signal.aborted) setData(result); }).catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Не удалось открыть ссылку.'); });
    return () => controller.abort();
  }, [token, attempt]);
  return <div className="app-shell page">
    <header className="flex items-center gap-3 mb-7"><div className="icon-tile"><Leaf className="w-5 h-5" /></div><p className="eyebrow">Hookah · от друга</p></header>
    {error ? <Card><h1 className="mb-4">Ссылка недоступна</h1><p role="alert" className="text-tg-hint mb-4">{error}</p><Button onClick={() => setAttempt(value => value + 1)}>Попробовать снова</Button></Card> : !data ? <p role="status" className="text-tg-hint">Открываем ссылку…</p> : <>
      <h1 className="mb-2">{data.title}</h1>
      <p className="text-sm text-tg-hint mb-6">{data.kind === 'mix' ? 'Сохранённое сочетание' : `${data.tobaccos?.length || 0} в коллекции`} · {new Date(data.created_at * 1000).toLocaleDateString('ru-RU')}</p>
      {data.kind === 'collection' ? <div className="space-y-2">{data.tobaccos?.map((item, index) => <Card key={index}><div className="flex items-center gap-3"><div className="icon-tile"><Package className="w-5 h-5" /></div><div className="min-w-0"><h2 className="font-semibold break-words">{item.name}</h2>{item.brand && <p className="text-sm text-tg-hint break-words">{item.brand}</p>}</div></div></Card>)}</div> : <Card>
        <h2 className="eyebrow mb-4">Состав</h2><div className="space-y-3">{data.components?.map((item, index) => <div key={index} className="flex gap-4 items-start justify-between p-3 rounded-xl bg-tg-secondary-bg"><div className="min-w-0"><p className="font-medium break-words">{item.name}</p><p className="text-xs text-tg-hint mt-1">{item.role}</p></div><strong className="text-tg-link shrink-0">{item.portion}%</strong></div>)}</div>
        {data.description && <p className="mt-5 leading-relaxed break-words">{data.description}</p>}
        {data.tips && <div className="mt-5 p-4 rounded-xl bg-tg-secondary-bg"><h3 className="font-semibold text-sm mb-2">На заметку</h3><p className="text-sm break-words">{data.tips}</p></div>}
      </Card>}
      <p className="text-xs text-tg-hint mt-6">Снимок на момент отправки. Доступен до {new Date(data.expires_at * 1000).toLocaleDateString('ru-RU')}. Вы просматриваете его без доступа к аккаунту друга.</p>
    </>}
    <a className="inline-block text-sm text-tg-link mt-6 mb-8" href="/">Открыть своё приложение</a>
  </div>;
}

import { useEffect, useState } from 'react';
import { ArrowUpRight, Package, Star, ChevronRight, Leaf } from 'lucide-react';
import { useStore } from '../store';
import { userApi } from '../api';
import { ErrorState } from '../components/ErrorState';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { hapticFeedback, getTelegramUser } from '../telegram';

export function HomePage({ onOpenGuide }: { onOpenGuide?: () => void }) {
  const { stats, setStats, setCurrentTab, tobaccos } = useStore();
  const [error, setError] = useState<string | null>(null);
  const loadStats = async () => {
    setError(null);
    try { setStats(await userApi.getStats()); }
    catch (err) { setError(err instanceof Error ? err.message : 'Не удалось загрузить данные.'); }
  };
  useEffect(() => { void loadStats(); }, [tobaccos.length]);
  const firstName = getTelegramUser()?.first_name;
  const go = (tab: 'mix' | 'collection' | 'favorites') => { hapticFeedback.light(); setCurrentTab(tab); };
  if (error) return <ErrorState message={error} onRetry={loadStats} />;
  return <div className="page">
    <header className="flex items-center justify-between mb-7">
      <div className="min-w-0"><p className="eyebrow mb-2">Hookah · моя коллекция</p><h1>{firstName ? `Привет, ${firstName}` : 'Ваш вкус. Ваш микс.'}</h1></div>
      <div className="icon-tile ml-3" aria-hidden="true"><Leaf className="w-5 h-5" /></div>
    </header>
    <section className="hero">
      <div className="hero-art" aria-hidden="true" />
      <p className="eyebrow mb-4" style={{color:'#dce9b8'}}>Найти сочетание</p>
      <h2>Сегодня —<br />новый микс.</h2>
      <p className="mt-4">Сочетания из табаков, которые уже есть у вас.</p>
      <button className="hero-cta tap-highlight" onClick={() => go('mix')}>Подобрать микс <ArrowUpRight className="w-4 h-4" /></button>
    </section>
    <div className="grid grid-cols-3 my-5" aria-label="Ваша статистика">
      <div className="home-stat"><strong>{stats?.tobaccos_count ?? '—'}</strong><span>в коллекции</span></div>
      <div className="home-stat"><strong>{stats?.mixes_count ?? '—'}</strong><span>миксов</span></div>
      <div className="home-stat"><strong>{stats?.favorites_count ?? '—'}</strong><span>избранных</span></div>
    </div>
    {onOpenGuide && <div className="mb-5"><Button variant="ghost" size="sm" onClick={onOpenGuide}>Как пользоваться</Button></div>}
    <h2 className="eyebrow mb-3">Под рукой</h2>
    <div className="space-y-3">
      <Card onClick={() => go('collection')}>
        <div className="flex items-center gap-4"><div className="icon-tile"><Package className="w-5 h-5" /></div><div className="flex-1"><h3 className="font-semibold">Моя коллекция</h3><p className="text-sm text-tg-hint mt-1">Все вкусы в одном месте</p></div><ChevronRight className="w-4 h-4 text-tg-hint" /></div>
      </Card>
      <Card onClick={() => go('favorites')}>
        <div className="flex items-center gap-4"><div className="icon-tile"><Star className="w-5 h-5" /></div><div className="flex-1"><h3 className="font-semibold">Любимые сочетания</h3><p className="text-sm text-tg-hint mt-1">Миксы, к которым хочется вернуться</p></div><ChevronRight className="w-4 h-4 text-tg-hint" /></div>
      </Card>
    </div>
  </div>;
}

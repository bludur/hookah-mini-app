import { useEffect, useState } from 'react';
import { Package, Palette, Star, ChevronRight, Cigarette } from 'lucide-react';
import { useStore } from '../store';
import { userApi } from '../api';
import { ErrorState } from '../components/ErrorState';
import { Card } from '../components/Card';
import { hapticFeedback, getTelegramUser } from '../telegram';

export function HomePage() {
  const { stats, setStats, setCurrentTab, tobaccos } = useStore();

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, [tobaccos.length]);

  const loadStats = async () => {
    setError(null);
    try {
      const data = await userApi.getStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить статистику.');
    }
  };

  const user = getTelegramUser();
  const firstName = user?.first_name || 'друг';

  const quickActions = [
    {
      id: 'collection',
      icon: Package,
      label: 'Коллекция',
      description: `${stats?.tobaccos_count || 0} табаков`,
      color: 'bg-blue-500',
      tab: 'collection' as const,
    },
    {
      id: 'mix',
      icon: Palette,
      label: 'Подобрать микс',
      description: 'AI составит микс',
      color: 'bg-purple-500',
      tab: 'mix' as const,
    },
    {
      id: 'favorites',
      icon: Star,
      label: 'Избранное',
      description: `${stats?.favorites_count || 0} миксов`,
      color: 'bg-yellow-500',
      tab: 'favorites' as const,
    },
  ];

  const handleQuickAction = (tab: typeof quickActions[number]['tab']) => {
    hapticFeedback.light();
    setCurrentTab(tab);
  };

  if (error) return <ErrorState message={error} onRetry={loadStats} />;

  return (
    <div className="min-h-screen pb-20 px-4 pt-4">
      {/* Welcome Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-tg-text">
          Привет, {firstName}! 👋
        </h1>
        <p className="text-tg-hint mt-1">
          Что будем делать сегодня?
        </p>
      </div>

      {/* Stats Card */}
      <Card className="mb-6 bg-gradient-to-br from-tg-button to-purple-600">
        <div className="flex items-center justify-between text-white">
          <div>
            <p className="text-white/80 text-sm">Всего миксов создано</p>
            <p className="text-3xl font-bold">{stats?.mixes_count || 0}</p>
          </div>
          <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center">
            <Cigarette className="w-8 h-8" />
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <h2 className="text-lg font-semibold text-tg-text mb-3">Быстрые действия</h2>
      <div className="space-y-3">
        {quickActions.map(({ id, icon: Icon, label, description, color, tab }) => (
          <Card
            key={id}
            onClick={() => handleQuickAction(tab)}
            padding="none"
            className="overflow-hidden"
          >
            <div className="flex items-center p-4">
              <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center mr-4`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-tg-text">{label}</h3>
                <p className="text-sm text-tg-hint">{description}</p>
              </div>
              <ChevronRight className="w-5 h-5 text-tg-hint" />
            </div>
          </Card>
        ))}
      </div>

      {/* Tips */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-tg-text mb-3">Как это работает</h2>
        <Card className="bg-tg-secondary-bg">
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-tg-button text-tg-button-text flex items-center justify-center text-sm font-bold shrink-0">
                1
              </div>
              <div>
                <p className="font-medium text-tg-text">Добавь табаки</p>
                <p className="text-sm text-tg-hint">Внеси свою коллекцию табаков</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-tg-button text-tg-button-text flex items-center justify-center text-sm font-bold shrink-0">
                2
              </div>
              <div>
                <p className="font-medium text-tg-text">Попроси микс</p>
                <p className="text-sm text-tg-hint">AI подберёт идеальное сочетание</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-tg-button text-tg-button-text flex items-center justify-center text-sm font-bold shrink-0">
                3
              </div>
              <div>
                <p className="font-medium text-tg-text">Оценивай</p>
                <p className="text-sm text-tg-hint">AI запомнит твои предпочтения!</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

import { ShareButton } from '../components/ShareButton';
import { ErrorState } from '../components/ErrorState';
import { useState, useEffect } from 'react';
import { History, ThumbsUp, ThumbsDown, Star, Clock } from 'lucide-react';
import { useStore } from '../store';
import { mixesApi, Mix } from '../api';
import { Card } from '../components/Card';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { Loader } from '../components/Loader';
import { hapticFeedback } from '../telegram';

const roleEmojis: Record<string, string> = {
  'база': '🔵',
  'дополнение': '🟢',
  'акцент': '🟡',
};

export function HistoryPage() {
  const { mixes, setMixes } = useStore();
  const [loadError, setLoadError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMix, setSelectedMix] = useState<Mix | null>(null);

  useEffect(() => {
    loadMixes();
  }, []);

  const loadMixes = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await mixesApi.getAll();
      setMixes(data);
      setHasMore(data.length === 20);
      setMoreError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Не удалось загрузить данные.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRatingIcon = (rating: number | null) => {
    if (rating === 1) return <ThumbsUp className="w-4 h-4 text-green-500" />;
    if (rating === -1) return <ThumbsDown className="w-4 h-4 text-red-500" />;
    return null;
  };

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    setMoreError(null);
    try {
      const next = await mixesApi.getAll(20, mixes.length);
      setMixes([...mixes, ...next.filter(item => !mixes.some(existing => existing.id === item.id))]);
      setHasMore(next.length === 20);
    } catch (err) {
      setMoreError(err instanceof Error ? err.message : 'Не удалось загрузить данные.');
    } finally {
      setLoadingMore(false);
    }
  };

  if (loadError) return <ErrorState message={loadError} onRetry={loadMixes} />;

  if (isLoading) {
    return <Loader text="Загрузка истории..." />;
  }

  return (
    <div className="page">
      <h1 className="text-2xl font-bold text-tg-text mb-4">
        История миксов
      </h1>

      {mixes.length === 0 ? (
        <EmptyState
          icon={<History className="w-16 h-16" />}
          title="История пуста"
          description="Здесь будут сохраняться созданные миксы"
        />
      ) : (
        <div className="space-y-3">
          {mixes.map((mix) => (
            <Card
              key={mix.id}
              onClick={() => {
                hapticFeedback.light();
                setSelectedMix(mix);
              }}
              padding="none"
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-tg-text flex-1">
                    {mix.name}
                  </h3>
                  <div className="flex items-center gap-1">
                    {mix.is_favorite && <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />}
                    {getRatingIcon(mix.rating)}
                  </div>
                </div>
                
                <p className="text-sm text-tg-hint mb-2">
                  {Object.keys(mix.components).slice(0, 3).join(', ')}
                  {Object.keys(mix.components).length > 3 && '...'}
                </p>

                <div className="flex items-center text-xs text-tg-hint">
                  <Clock className="w-3 h-3 mr-1" />
                  {formatDate(mix.created_at)}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Mix Details Modal */}
      {moreError && <p role="alert" className="mt-4 text-red-600">{moreError}</p>}
      {hasMore && <button className="mt-4 p-3 w-full text-tg-link" disabled={loadingMore} onClick={loadMore}>
        {loadingMore ? 'Загрузка...' : 'Загрузить ещё'}
      </button>}

      <Modal
        isOpen={!!selectedMix}
        onClose={() => setSelectedMix(null)}
        title={selectedMix?.name || 'Микс'}
      >
        {selectedMix && (
          <div className="space-y-4">
            <ShareButton kind="mix" mixId={selectedMix.id} />

            {/* Components */}
            <div>
              <h4 className="text-sm font-medium text-tg-hint uppercase tracking-wide mb-2">
                Состав
              </h4>
              <div className="space-y-2">
                {Object.entries(selectedMix.components).map(([tobacco, data]) => (
                  <div
                    key={tobacco}
                    className="flex items-center justify-between p-3 bg-tg-secondary-bg rounded-xl"
                  >
                    <div className="flex items-center gap-2">
                      <span>{roleEmojis[data.role] || '⚪'}</span>
                      <span className="font-medium text-tg-text">{tobacco}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-tg-button">{data.portion}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Description */}
            {selectedMix.description && (
              <div>
                <h4 className="text-sm font-medium text-tg-hint uppercase tracking-wide mb-2">
                  Описание
                </h4>
                <p className="text-tg-text">{selectedMix.description}</p>
              </div>
            )}

            {/* Tips */}
            {selectedMix.tips && (
              <div className="p-3 bg-yellow-50 rounded-xl">
                <h4 className="text-sm font-medium text-yellow-800 mb-1">💡 Совет</h4>
                <p className="text-sm text-yellow-700">{selectedMix.tips}</p>
              </div>
            )}

            {/* Meta */}
            <div className="text-sm text-tg-hint pt-2 border-t border-tg-secondary-bg">
              Создан {formatDate(selectedMix.created_at)}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

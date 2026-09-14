import { ErrorState } from '../components/ErrorState';
import { useState, useEffect } from 'react';
import { Star, Trash2 } from 'lucide-react';
import { useStore } from '../store';
import { mixesApi, Mix } from '../api';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { Loader } from '../components/Loader';
import { hapticFeedback, showConfirm } from '../telegram';

const roleEmojis: Record<string, string> = {
  'база': '🔵',
  'дополнение': '🟢',
  'акцент': '🟡',
};

export function FavoritesPage() {
  const { favorites, setFavorites } = useStore();
  const [loadError, setLoadError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMix, setSelectedMix] = useState<Mix | null>(null);

  useEffect(() => {
    loadFavorites();
  }, []);

  const loadFavorites = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await mixesApi.getFavorites();
      setFavorites(data);
      setHasMore(data.length === 20);
      setMoreError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Не удалось загрузить данные.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveFromFavorites = async (mix: Mix) => {
    const confirmed = await showConfirm('Убрать из избранного?');
    if (!confirmed) return;

    try {
      await mixesApi.toggleFavorite(mix.id, false);
      setFavorites(favorites.filter(f => f.id !== mix.id));
      hapticFeedback.success();
      setSelectedMix(null);
    } catch (err) {
      setMoreError(err instanceof Error ? err.message : 'Не удалось выполнить действие.');
      hapticFeedback.error();
    }
  };

  const handleClearAll = async () => {
    const confirmed = await showConfirm('Очистить всё избранное?');
    if (!confirmed) return;

    try {
      await mixesApi.clearFavorites();
      setFavorites([]);
      setHasMore(false);
      hapticFeedback.success();
    } catch (err) {
      setMoreError(err instanceof Error ? err.message : 'Не удалось выполнить действие.');
      hapticFeedback.error();
    }
  };

  const loadMore = async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    setMoreError(null);
    try {
      const next = await mixesApi.getFavorites(20, favorites.length);
      setFavorites([...favorites, ...next.filter(item => !favorites.some(existing => existing.id === item.id))]);
      setHasMore(next.length === 20);
    } catch (err) {
      setMoreError(err instanceof Error ? err.message : 'Не удалось загрузить данные.');
    } finally {
      setLoadingMore(false);
    }
  };

  if (loadError) return <ErrorState message={loadError} onRetry={loadFavorites} />;

  if (isLoading) {
    return <Loader text="Загрузка избранного..." />;
  }

  return (
    <div className="min-h-screen pb-20 px-4 pt-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-tg-text">
          Избранное
          <span className="text-tg-hint font-normal text-lg ml-2">
            ({favorites.length})
          </span>
        </h1>
        {favorites.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            icon={<Trash2 className="w-4 h-4" />}
          >
            Очистить
          </Button>
        )}
      </div>

      {favorites.length === 0 ? (
        <EmptyState
          icon={<Star className="w-16 h-16" />}
          title="Избранное пусто"
          description="Добавляй понравившиеся миксы, чтобы не потерять их"
        />
      ) : (
        <div className="space-y-3">
          {favorites.map((mix) => (
            <Card
              key={mix.id}
              onClick={() => {
                hapticFeedback.light();
                setSelectedMix(mix);
              }}
            >
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-xl bg-yellow-100 flex items-center justify-center">
                  <Star className="w-6 h-6 text-yellow-500 fill-yellow-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-tg-text truncate">
                    {mix.name}
                  </h3>
                  <p className="text-sm text-tg-hint truncate">
                    {Object.keys(mix.components).join(', ')}
                  </p>
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

            {/* Actions */}
            <Button
              fullWidth
              variant="danger"
              onClick={() => handleRemoveFromFavorites(selectedMix)}
              icon={<Trash2 className="w-5 h-5" />}
            >
              Убрать из избранного
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

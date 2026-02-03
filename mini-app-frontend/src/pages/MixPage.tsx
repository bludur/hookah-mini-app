import { useState, useEffect } from 'react';
import { Palette, Sparkles, Candy, Citrus, Leaf, ThumbsUp, ThumbsDown, Star, RefreshCw, AlertCircle } from 'lucide-react';
import { useStore } from '../store';
import { tobaccosApi, mixesApi } from '../api';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { EmptyState } from '../components/EmptyState';
import { Loader } from '../components/Loader';
import { hapticFeedback } from '../telegram';

const profileOptions = [
  { id: 'сладкий', icon: Candy, label: 'Сладкий', color: 'bg-pink-500' },
  { id: 'кислый', icon: Citrus, label: 'Кислый', color: 'bg-yellow-500' },
  { id: 'свежий', icon: Leaf, label: 'Свежий', color: 'bg-green-500' },
];

const roleEmojis: Record<string, string> = {
  'база': '🔵',
  'дополнение': '🟢',
  'акцент': '🟡',
};

export function MixPage() {
  const { tobaccos, setTobaccos, currentMix, setCurrentMix } = useStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBase, setSelectedBase] = useState<string | null>(null);
  const [showBaseSelector, setShowBaseSelector] = useState(false);

  useEffect(() => {
    if (tobaccos.length === 0) {
      loadTobaccos();
    }
  }, []);

  const loadTobaccos = async () => {
    setIsLoading(true);
    try {
      const data = await tobaccosApi.getAll();
      setTobaccos(data);
    } catch (err) {
      console.error('Failed to load tobaccos:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const generateMix = async (
    type: 'base' | 'profile' | 'surprise',
    baseTobacco?: string,
    tasteProfile?: string
  ) => {
    setIsGenerating(true);
    setError(null);
    setCurrentMix(null);
    
    try {
      const mix = await mixesApi.generate({
        request_type: type,
        base_tobacco: baseTobacco,
        taste_profile: tasteProfile,
      });
      setCurrentMix(mix);
      hapticFeedback.success();
    } catch (err: any) {
      setError(err.message);
      hapticFeedback.error();
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRateMix = async (rating: number) => {
    if (!currentMix) return;
    
    hapticFeedback.light();
    try {
      await mixesApi.rate(currentMix.id, rating);
      hapticFeedback.success();
    } catch (err) {
      hapticFeedback.error();
    }
  };

  const handleFavorite = async () => {
    if (!currentMix) return;
    
    hapticFeedback.light();
    try {
      await mixesApi.toggleFavorite(currentMix.id, true);
      hapticFeedback.success();
    } catch (err) {
      hapticFeedback.error();
    }
  };

  const handleRetry = () => {
    hapticFeedback.light();
    generateMix('surprise');
  };

  if (isLoading) {
    return <Loader text="Загрузка..." />;
  }

  if (tobaccos.length < 2) {
    return (
      <div className="min-h-screen pb-20 px-4 pt-4">
        <EmptyState
          icon={<AlertCircle className="w-16 h-16" />}
          title="Мало табаков"
          description="Для создания микса нужно минимум 2 табака в коллекции"
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-20 px-4 pt-4">
      <h1 className="text-2xl font-bold text-tg-text mb-4">
        Подбор микса
      </h1>

      {/* Options */}
      {!currentMix && !isGenerating && (
        <div className="space-y-4">
          {/* By Base Tobacco */}
          <Card>
            <h3 className="font-semibold text-tg-text mb-3">На основе табака</h3>
            {showBaseSelector ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {tobaccos.slice(0, 10).map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        hapticFeedback.selection();
                        setSelectedBase(t.name);
                      }}
                      className={`p-3 rounded-xl text-left text-sm transition-colors tap-highlight ${
                        selectedBase === t.name
                          ? 'bg-tg-button text-tg-button-text'
                          : 'bg-tg-secondary-bg text-tg-text'
                      }`}
                    >
                      {t.category?.emoji || '🔸'} {t.name}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2 mt-3">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setShowBaseSelector(false);
                      setSelectedBase(null);
                    }}
                  >
                    Отмена
                  </Button>
                  <Button
                    fullWidth
                    disabled={!selectedBase}
                    onClick={() => {
                      if (selectedBase) {
                        generateMix('base', selectedBase);
                        setShowBaseSelector(false);
                      }
                    }}
                  >
                    Создать микс
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="secondary"
                fullWidth
                onClick={() => {
                  hapticFeedback.light();
                  setShowBaseSelector(true);
                }}
              >
                Выбрать табак
              </Button>
            )}
          </Card>

          {/* By Profile */}
          <Card>
            <h3 className="font-semibold text-tg-text mb-3">По вкусовому профилю</h3>
            <div className="grid grid-cols-3 gap-2">
              {profileOptions.map(({ id, icon: Icon, label, color }) => (
                <button
                  key={id}
                  onClick={() => {
                    hapticFeedback.light();
                    generateMix('profile', undefined, id);
                  }}
                  className={`${color} text-white p-4 rounded-xl flex flex-col items-center gap-2 tap-highlight transition-transform active:scale-95`}
                >
                  <Icon className="w-6 h-6" />
                  <span className="text-sm font-medium">{label}</span>
                </button>
              ))}
            </div>
          </Card>

          {/* Surprise */}
          <Card
            onClick={() => {
              hapticFeedback.medium();
              generateMix('surprise');
            }}
            className="bg-gradient-to-br from-purple-500 to-pink-500 text-white cursor-pointer"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-white/20 flex items-center justify-center">
                <Sparkles className="w-7 h-7" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Удиви меня!</h3>
                <p className="text-white/80 text-sm">AI подберёт креативный микс</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Loading State */}
      {isGenerating && (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-20 h-20 rounded-full bg-tg-button/20 flex items-center justify-center mb-4 animate-pulse-slow">
            <Palette className="w-10 h-10 text-tg-button animate-spin" style={{ animationDuration: '3s' }} />
          </div>
          <p className="text-tg-text font-medium">Составляю микс...</p>
          <p className="text-tg-hint text-sm">Это займёт несколько секунд</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="bg-red-50 border border-red-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-500 shrink-0" />
            <div>
              <h3 className="font-medium text-red-800">Ошибка</h3>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
          <Button
            variant="secondary"
            fullWidth
            className="mt-4"
            onClick={() => setError(null)}
          >
            Попробовать снова
          </Button>
        </Card>
      )}

      {/* Mix Result */}
      {currentMix && !isGenerating && (
        <div className="space-y-4 animate-fade-in">
          <Card className="bg-gradient-to-br from-tg-button/10 to-purple-500/10">
            <h2 className="text-2xl font-bold text-tg-text mb-4">
              🎨 {currentMix.name}
            </h2>

            {/* Components */}
            <div className="space-y-3 mb-4">
              <h4 className="text-sm font-medium text-tg-hint uppercase tracking-wide">
                Состав
              </h4>
              {currentMix.components.map((comp, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-tg-section-bg rounded-xl"
                >
                  <div className="flex items-center gap-2">
                    <span>{roleEmojis[comp.role] || '⚪'}</span>
                    <span className="font-medium text-tg-text">{comp.tobacco}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-tg-button">{comp.portion}%</span>
                    <span className="text-xs text-tg-hint">({comp.role})</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Description */}
            <div className="mb-4">
              <h4 className="text-sm font-medium text-tg-hint uppercase tracking-wide mb-2">
                Описание
              </h4>
              <p className="text-tg-text">{currentMix.description}</p>
            </div>

            {/* Tips */}
            <div className="p-3 bg-yellow-50 rounded-xl">
              <h4 className="text-sm font-medium text-yellow-800 mb-1">💡 Совет</h4>
              <p className="text-sm text-yellow-700">{currentMix.tips}</p>
            </div>
          </Card>

          {/* Actions */}
          <div className="grid grid-cols-4 gap-2">
            <Button
              variant="secondary"
              onClick={() => handleRateMix(1)}
              className="flex-col py-3"
            >
              <ThumbsUp className="w-5 h-5 mb-1" />
              <span className="text-xs">Нравится</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleRateMix(-1)}
              className="flex-col py-3"
            >
              <ThumbsDown className="w-5 h-5 mb-1" />
              <span className="text-xs">Не то</span>
            </Button>
            <Button
              variant="secondary"
              onClick={handleFavorite}
              className="flex-col py-3"
            >
              <Star className="w-5 h-5 mb-1" />
              <span className="text-xs">Избранное</span>
            </Button>
            <Button
              variant="secondary"
              onClick={handleRetry}
              className="flex-col py-3"
            >
              <RefreshCw className="w-5 h-5 mb-1" />
              <span className="text-xs">Другой</span>
            </Button>
          </div>

          {/* Back Button */}
          <Button
            variant="ghost"
            fullWidth
            onClick={() => {
              setCurrentMix(null);
              setSelectedBase(null);
            }}
          >
            ← К выбору
          </Button>
        </div>
      )}
    </div>
  );
}

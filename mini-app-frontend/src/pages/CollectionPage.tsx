import { useState, useEffect } from 'react';
import { Plus, Search, Trash2, Package, ListPlus, X } from 'lucide-react';
import { useStore } from '../store';
import { tobaccosApi, categoriesApi, Tobacco } from '../api';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { Loader } from '../components/Loader';
import { hapticFeedback, showConfirm } from '../telegram';

export function CollectionPage() {
  const { tobaccos, setTobaccos, addTobacco, removeTobacco, categories, setCategories } = useStore();
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showTobaccoModal, setShowTobaccoModal] = useState(false);
  const [selectedTobacco, setSelectedTobacco] = useState<Tobacco | null>(null);

  // Form state
  const [newName, setNewName] = useState('');
  const [newBrand, setNewBrand] = useState('');
  const [newCategoryId, setNewCategoryId] = useState<number | null>(null);
  const [bulkText, setBulkText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [tobaccosData, categoriesData] = await Promise.all([
        tobaccosApi.getAll(),
        categoriesApi.getAll(),
      ]);
      setTobaccos(tobaccosData);
      setCategories(categoriesData);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddTobacco = async () => {
    if (!newName.trim()) return;
    
    setIsSubmitting(true);
    try {
      const tobacco = await tobaccosApi.create({
        name: newName.trim(),
        brand: newBrand.trim() || undefined,
        category_id: newCategoryId || undefined,
      });
      addTobacco(tobacco);
      hapticFeedback.success();
      setShowAddModal(false);
      resetForm();
    } catch (err: any) {
      hapticFeedback.error();
      alert(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBulkAdd = async () => {
    if (!bulkText.trim()) return;
    
    const lines = bulkText.split('\n').filter(l => l.trim());
    const tobaccos = lines.map(line => {
      const parts = line.split('|').map(p => p.trim());
      return {
        name: parts[0],
        brand: parts[1] || undefined,
        category_id: undefined,
      };
    });

    setIsSubmitting(true);
    try {
      const result = await tobaccosApi.createBulk(tobaccos);
      hapticFeedback.success();
      setShowBulkModal(false);
      setBulkText('');
      loadData();
      
      let message = `Добавлено: ${result.added.length}`;
      if (result.skipped.length > 0) {
        message += `\nПропущено: ${result.skipped.length}`;
      }
      if (result.errors.length > 0) {
        message += `\nОшибок: ${result.errors.length}`;
      }
      alert(message);
    } catch (err: any) {
      hapticFeedback.error();
      alert(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteTobacco = async (id: number) => {
    const confirmed = await showConfirm('Удалить табак из коллекции?');
    if (!confirmed) return;

    try {
      await tobaccosApi.delete(id);
      removeTobacco(id);
      hapticFeedback.success();
      setShowTobaccoModal(false);
    } catch (err: any) {
      hapticFeedback.error();
      alert(err.message);
    }
  };

  const resetForm = () => {
    setNewName('');
    setNewBrand('');
    setNewCategoryId(null);
  };

  const openTobaccoDetails = (tobacco: Tobacco) => {
    hapticFeedback.light();
    setSelectedTobacco(tobacco);
    setShowTobaccoModal(true);
  };

  const filteredTobaccos = tobaccos.filter(t =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.brand && t.brand.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (isLoading) {
    return <Loader text="Загрузка коллекции..." />;
  }

  return (
    <div className="min-h-screen pb-20 px-4 pt-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-tg-text">
          Коллекция
          <span className="text-tg-hint font-normal text-lg ml-2">
            ({tobaccos.length})
          </span>
        </h1>
      </div>

      {/* Search & Actions */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-tg-hint" />
          <input
            type="text"
            placeholder="Поиск..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-tg-secondary-bg text-tg-text placeholder-tg-hint focus:outline-none"
          />
        </div>
        <Button
          onClick={() => {
            hapticFeedback.light();
            setShowAddModal(true);
          }}
          icon={<Plus className="w-5 h-5" />}
        >
          {''}
        </Button>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2 mb-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            hapticFeedback.light();
            setShowBulkModal(true);
          }}
          icon={<ListPlus className="w-4 h-4" />}
        >
          Добавить список
        </Button>
      </div>

      {/* Tobaccos List */}
      {filteredTobaccos.length === 0 ? (
        <EmptyState
          icon={<Package className="w-16 h-16" />}
          title="Коллекция пуста"
          description="Добавь табаки, чтобы начать создавать миксы"
          action={
            <Button onClick={() => setShowAddModal(true)} icon={<Plus className="w-5 h-5" />}>
              Добавить табак
            </Button>
          }
        />
      ) : (
        <div className="space-y-2">
          {filteredTobaccos.map((tobacco) => (
            <Card
              key={tobacco.id}
              onClick={() => openTobaccoDetails(tobacco)}
              padding="none"
            >
              <div className="flex items-center p-3">
                <span className="text-2xl mr-3">
                  {tobacco.category?.emoji || '🔸'}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-tg-text truncate">{tobacco.name}</p>
                  {tobacco.brand && (
                    <p className="text-sm text-tg-hint truncate">{tobacco.brand}</p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Add Tobacco Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          resetForm();
        }}
        title="Добавить табак"
      >
        <div className="space-y-4">
          <Input
            label="Название"
            placeholder="Например: Манго"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Input
            label="Бренд (опционально)"
            placeholder="Например: Darkside"
            value={newBrand}
            onChange={(e) => setNewBrand(e.target.value)}
          />
          <div>
            <label className="block text-sm font-medium text-tg-text mb-2">
              Категория
            </label>
            <div className="grid grid-cols-2 gap-2">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => {
                    hapticFeedback.selection();
                    setNewCategoryId(newCategoryId === cat.id ? null : cat.id);
                  }}
                  className={`p-3 rounded-xl text-left transition-colors tap-highlight ${
                    newCategoryId === cat.id
                      ? 'bg-tg-button text-tg-button-text'
                      : 'bg-tg-secondary-bg text-tg-text'
                  }`}
                >
                  <span className="mr-2">{cat.emoji}</span>
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
          <Button
            fullWidth
            onClick={handleAddTobacco}
            loading={isSubmitting}
            disabled={!newName.trim()}
          >
            Добавить
          </Button>
        </div>
      </Modal>

      {/* Bulk Add Modal */}
      <Modal
        isOpen={showBulkModal}
        onClose={() => {
          setShowBulkModal(false);
          setBulkText('');
        }}
        title="Добавить список"
      >
        <div className="space-y-4">
          <p className="text-sm text-tg-hint">
            Введите табаки, каждый с новой строки.
            <br />
            Формат: <code className="bg-tg-secondary-bg px-1 rounded">Название | Бренд</code>
          </p>
          <textarea
            placeholder="Манго | Darkside
Мята
Клубника | Fumari"
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            className="w-full h-40 px-4 py-3 rounded-xl bg-tg-secondary-bg text-tg-text placeholder-tg-hint focus:outline-none resize-none"
          />
          <Button
            fullWidth
            onClick={handleBulkAdd}
            loading={isSubmitting}
            disabled={!bulkText.trim()}
          >
            Добавить
          </Button>
        </div>
      </Modal>

      {/* Tobacco Details Modal */}
      <Modal
        isOpen={showTobaccoModal}
        onClose={() => {
          setShowTobaccoModal(false);
          setSelectedTobacco(null);
        }}
        title={selectedTobacco?.name || 'Табак'}
      >
        {selectedTobacco && (
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <span className="text-5xl">
                {selectedTobacco.category?.emoji || '🔸'}
              </span>
              <div>
                <h3 className="text-xl font-bold text-tg-text">
                  {selectedTobacco.name}
                </h3>
                {selectedTobacco.brand && (
                  <p className="text-tg-hint">{selectedTobacco.brand}</p>
                )}
              </div>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between py-2 border-b border-tg-secondary-bg">
                <span className="text-tg-hint">Категория</span>
                <span className="text-tg-text">
                  {selectedTobacco.category?.name || 'Не указана'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-tg-secondary-bg">
                <span className="text-tg-hint">Добавлен</span>
                <span className="text-tg-text">
                  {new Date(selectedTobacco.created_at).toLocaleDateString('ru-RU')}
                </span>
              </div>
            </div>

            <Button
              fullWidth
              variant="danger"
              onClick={() => handleDeleteTobacco(selectedTobacco.id)}
              icon={<Trash2 className="w-5 h-5" />}
            >
              Удалить
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

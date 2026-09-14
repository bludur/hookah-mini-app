import { ShareButton } from '../components/ShareButton';
import { ErrorState } from '../components/ErrorState';
import { PhotoImport } from '../components/PhotoImport';
import { useState, useEffect } from 'react';
import { Plus, Search, Trash2, Package, ListPlus, ChevronRight } from 'lucide-react';
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
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showTobaccoModal, setShowTobaccoModal] = useState(false);
  const [selectedTobacco, setSelectedTobacco] = useState<Tobacco | null>(null);

  // Form state
  const [editingId, setEditingId] = useState<number | null>(null);
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
    setLoadError(null);
    try {
      const [tobaccosData, categoriesData] = await Promise.all([
        tobaccosApi.getAll(),
        categoriesApi.getAll(),
      ]);
      setTobaccos(tobaccosData);
      setCategories(categoriesData);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Не удалось загрузить данные.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddTobacco = async () => {
    if (!newName.trim()) return;
    
    setIsSubmitting(true);
    try {
      const tobacco = editingId ? await tobaccosApi.update(editingId, {
        name: newName.trim(), brand: newBrand.trim() || null, category_id: newCategoryId,
      }) : await tobaccosApi.create({
        name: newName.trim(),
        brand: newBrand.trim() || undefined,
        category_id: newCategoryId || undefined,
      });
      if (editingId) setTobaccos(tobaccos.map(item => item.id === editingId ? tobacco : item).sort((a, b) => a.name.localeCompare(b.name)));
      else addTobacco(tobacco);
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
    setEditingId(null);
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

  if (loadError) return <ErrorState message={loadError} onRetry={loadData} />;

  if (isLoading) {
    return <Loader text="Загрузка коллекции..." />;
  }

  return (
    <div className="page">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-tg-text">
          Коллекция
          <span className="count-badge ml-2">
            {tobaccos.length}
          </span>
        </h1>
      </div>

      {/* Search & Actions */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-tg-hint" />
          <input
            type="text"
            aria-label="Поиск по коллекции"
            placeholder="Название или бренд"
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
          Добавить
        </Button>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 mb-6">
        <PhotoImport catalog={tobaccos} onAdded={() => { tobaccosApi.getAll().then(setTobaccos).catch(() => setLoadError('Обновите коллекцию, чтобы увидеть добавленные табаки.')); }} />
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

      <div className="mb-5"><ShareButton kind="collection" /></div>

      {/* Tobaccos List */}
      {filteredTobaccos.length === 0 ? (
        <EmptyState
          icon={<Package className="w-16 h-16" />}
          title={searchQuery ? "Ничего не нашлось" : "Коллекция пуста"}
          description={searchQuery ? "Попробуйте другое название или бренд" : "Добавьте первый вкус — по фото или вручную"}
          action={searchQuery ? <Button variant="secondary" onClick={() => setSearchQuery('')}>Сбросить поиск</Button> :
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
              <div className="flex items-center gap-3 p-4">
                <span className="icon-tile text-xl">
                  {tobacco.category?.emoji || '🔸'}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-tg-text truncate">{tobacco.name}</p>
                  {tobacco.brand && (
                    <p className="text-sm text-tg-hint truncate">{tobacco.brand}</p>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-tg-hint" />
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
        title={editingId ? "Изменить табак" : "Добавить табак"}
      >
        <div className="space-y-2">
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                aria-label="Название"
                minLength={2}
                maxLength={100}
                placeholder="Название"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="w-28">
              <Input
                aria-label="Бренд"
                maxLength={100}
                placeholder="Бренд"
                value={newBrand}
                onChange={(e) => setNewBrand(e.target.value)}
              />
            </div>
          </div>
          <select
            aria-label="Категория"
            value={newCategoryId || ''}
            onChange={(e) => {
              hapticFeedback.selection();
              setNewCategoryId(e.target.value ? Number(e.target.value) : null);
            }}
            className="w-full px-3 py-2 rounded-lg text-sm bg-tg-secondary-bg text-tg-text focus:outline-none"
          >
            <option value="">Без категории</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.emoji} {cat.name}
              </option>
            ))}
          </select>
          <Button
            fullWidth
            onClick={handleAddTobacco}
            loading={isSubmitting}
            disabled={newName.trim().length < 2}
            size="sm"
          >
            {editingId ? "Сохранить" : "Добавить"}
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
        <div className="space-y-3">
          <p className="text-sm text-tg-hint">
            Введите табаки, каждый с новой строки.
            Формат: <code className="bg-tg-secondary-bg px-1 rounded">Название | Бренд</code>
          </p>
          <textarea
            placeholder="Манго | Darkside
Мята
Клубника | Fumari"
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            className="w-full h-32 px-4 py-3 rounded-xl bg-tg-secondary-bg text-tg-text placeholder-tg-hint focus:outline-none resize-none"
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
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-4xl">
                {selectedTobacco.category?.emoji || '🔸'}
              </span>
              <div>
                <h3 className="text-lg font-bold text-tg-text">
                  {selectedTobacco.name}
                </h3>
                {selectedTobacco.brand && (
                  <p className="text-tg-hint text-sm">{selectedTobacco.brand}</p>
                )}
              </div>
            </div>
            
            <div className="text-sm">
              <div className="flex justify-between py-2 border-b border-tg-secondary-bg">
                <span className="text-tg-hint">Категория</span>
                <span className="text-tg-text">
                  {selectedTobacco.category?.name || 'Не указана'}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-tg-hint">Добавлен</span>
                <span className="text-tg-text">
                  {new Date(selectedTobacco.created_at).toLocaleDateString('ru-RU')}
                </span>
              </div>
            </div>

            <Button fullWidth variant="secondary" onClick={() => {
              setEditingId(selectedTobacco.id);
              setNewName(selectedTobacco.name);
              setNewBrand(selectedTobacco.brand || '');
              setNewCategoryId(selectedTobacco.category_id);
              setShowTobaccoModal(false);
              setShowAddModal(true);
            }}>Изменить</Button>

            <Button
              fullWidth
              variant="danger"
              onClick={() => handleDeleteTobacco(selectedTobacco.id)}
              icon={<Trash2 className="w-4 h-4" />}
            >
              Удалить
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

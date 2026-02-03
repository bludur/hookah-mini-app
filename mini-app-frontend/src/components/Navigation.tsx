import { Home, Package, Palette, History, Star } from 'lucide-react';
import { useStore } from '../store';
import { hapticFeedback } from '../telegram';

const tabs = [
  { id: 'home' as const, icon: Home, label: 'Главная' },
  { id: 'collection' as const, icon: Package, label: 'Коллекция' },
  { id: 'mix' as const, icon: Palette, label: 'Микс' },
  { id: 'history' as const, icon: History, label: 'История' },
  { id: 'favorites' as const, icon: Star, label: 'Избранное' },
];

export function Navigation() {
  const { currentTab, setCurrentTab } = useStore();

  const handleTabClick = (tabId: typeof tabs[number]['id']) => {
    hapticFeedback.light();
    setCurrentTab(tabId);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-tg-section-bg border-t border-tg-secondary-bg safe-area-bottom z-50">
      <div className="flex justify-around items-center h-16 px-2">
        {tabs.map(({ id, icon: Icon, label }) => {
          const isActive = currentTab === id;
          return (
            <button
              key={id}
              onClick={() => handleTabClick(id)}
              className={`flex flex-col items-center justify-center flex-1 h-full tap-highlight transition-colors ${
                isActive ? 'text-tg-button' : 'text-tg-hint'
              }`}
            >
              <Icon className="w-6 h-6 mb-1" strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-xs font-medium">{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

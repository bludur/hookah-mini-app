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
    <nav className="app-nav" aria-label="Основная навигация">
      <div className="flex justify-around items-center gap-1">
        {tabs.map(({ id, icon: Icon, label }) => {
          const isActive = currentTab === id;
          return (
            <button
              key={id}
              onClick={() => handleTabClick(id)}
              aria-current={isActive ? 'page' : undefined}
              className="nav-item tap-highlight"
            >
              <Icon className="w-5 h-5" strokeWidth={isActive ? 2.5 : 2} />
              <span className="font-medium">{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

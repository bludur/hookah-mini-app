import { useEffect } from 'react';
import { useStore } from './store';
import { initTelegram, isTelegramWebApp } from './telegram';
import { Navigation } from './components/Navigation';
import { HomePage } from './pages/HomePage';
import { CollectionPage } from './pages/CollectionPage';
import { MixPage } from './pages/MixPage';
import { HistoryPage } from './pages/HistoryPage';
import { FavoritesPage } from './pages/FavoritesPage';

function App() {
  const { currentTab } = useStore();

  useEffect(() => {
    initTelegram();
  }, []);

  if (!isTelegramWebApp()) {
    return <div className="p-6 text-tg-text" role="alert">
      <h1 className="text-xl font-bold mb-3">Откройте приложение в Telegram</h1>
      <p>Перейдите в личный чат с ботом и нажмите кнопку приложения.</p>
    </div>;
  }

  const renderPage = () => {
    switch (currentTab) {
      case 'home':
        return <HomePage />;
      case 'collection':
        return <CollectionPage />;
      case 'mix':
        return <MixPage />;
      case 'history':
        return <HistoryPage />;
      case 'favorites':
        return <FavoritesPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="min-h-screen bg-tg-bg">
      <main className="pb-16">
        {renderPage()}
      </main>
      <Navigation />
    </div>
  );
}

export default App;

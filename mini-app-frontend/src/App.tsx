import { useEffect } from 'react';
import { useStore } from './store';
import { initTelegram } from './telegram';
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

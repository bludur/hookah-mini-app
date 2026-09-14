import { SharedPage } from './pages/SharedPage';
import { Onboarding, needsOnboarding, completeOnboarding } from './components/Onboarding';
import { useEffect, useState } from 'react';
import { useStore } from './store';
import { initTelegram, isTelegramWebApp, tg } from './telegram';
import { Navigation } from './components/Navigation';
import { HomePage } from './pages/HomePage';
import { CollectionPage } from './pages/CollectionPage';
import { MixPage } from './pages/MixPage';
import { HistoryPage } from './pages/HistoryPage';
import { FavoritesPage } from './pages/FavoritesPage';

function App() {
  const { currentTab, setCurrentTab } = useStore();
  const [showOnboarding, setShowOnboarding] = useState(needsOnboarding);
  const closeOnboarding = () => { completeOnboarding(); setShowOnboarding(false); };
  const readShare = () => window.location.hash.startsWith('#share=') ? window.location.hash.slice(7) : null;
  const [shareToken, setShareToken] = useState(readShare);
  useEffect(() => { const update = () => setShareToken(readShare()); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update); }, []);

  useEffect(() => {
    initTelegram();
    const applyTheme = () => { document.documentElement.dataset.theme = tg?.colorScheme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); };
    applyTheme();
    const observer = new MutationObserver(applyTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['style'] });
    return () => observer.disconnect();
  }, []);

  if (shareToken !== null) return <SharedPage token={shareToken} />;

  if (!isTelegramWebApp()) {
    return <div className="app-shell page text-tg-text" role="alert">
      <p className="eyebrow mb-5">Hookah · моя коллекция</p>
      <h1 className="mb-4">Откройте приложение в Telegram</h1>
      <p className="text-tg-hint leading-relaxed">Перейдите в чат с ботом и нажмите кнопку приложения. Ваша коллекция будет ждать вас там.</p>
    </div>;
  }

  const renderPage = () => {
    switch (currentTab) {
      case 'home':
        return <HomePage onOpenGuide={() => setShowOnboarding(true)} />;
      case 'collection':
        return <CollectionPage />;
      case 'mix':
        return <MixPage />;
      case 'history':
        return <HistoryPage />;
      case 'favorites':
        return <FavoritesPage />;
      default:
        return <HomePage onOpenGuide={() => setShowOnboarding(true)} />;
    }
  };

  return (
    <div className="app-shell min-h-screen bg-tg-bg">
      <main className="app-main">
        {renderPage()}
      </main>
      <Navigation />
      {showOnboarding && <Onboarding onClose={closeOnboarding} onStart={() => { closeOnboarding(); setCurrentTab('collection'); }} />}
    </div>
  );
}

export default App;

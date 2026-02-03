// Telegram WebApp utilities

export const tg = window.Telegram?.WebApp;

export const isTelegramWebApp = (): boolean => {
  return !!tg && !!tg.initData;
};

export const getTelegramUser = () => {
  if (!tg) return null;
  return tg.initDataUnsafe?.user || null;
};

export const hapticFeedback = {
  light: () => tg?.HapticFeedback?.impactOccurred('light'),
  medium: () => tg?.HapticFeedback?.impactOccurred('medium'),
  heavy: () => tg?.HapticFeedback?.impactOccurred('heavy'),
  success: () => tg?.HapticFeedback?.notificationOccurred('success'),
  error: () => tg?.HapticFeedback?.notificationOccurred('error'),
  warning: () => tg?.HapticFeedback?.notificationOccurred('warning'),
  selection: () => tg?.HapticFeedback?.selectionChanged(),
};

export const showAlert = (message: string): Promise<void> => {
  return new Promise((resolve) => {
    if (tg) {
      tg.showAlert(message, resolve);
    } else {
      alert(message);
      resolve();
    }
  });
};

export const showConfirm = (message: string): Promise<boolean> => {
  return new Promise((resolve) => {
    if (tg) {
      tg.showConfirm(message, resolve);
    } else {
      resolve(confirm(message));
    }
  });
};

export const initTelegram = () => {
  if (tg) {
    tg.ready();
    tg.expand();
  }
};

// Моковый пользователь для разработки вне Telegram
export const getMockUser = () => ({
  id: 123456789,
  first_name: 'Test',
  username: 'test_user',
});

import { useState } from 'react';
import { Camera, Sparkles, Share2 } from 'lucide-react';
import { getTelegramUser } from '../telegram';
import { Button } from './Button';
import { Modal } from './Modal';

const storageKey = () => `hookah:onboarding:v1:${getTelegramUser()?.id ?? 'guest'}`;
const completedThisSession = new Set<string>();

export function needsOnboarding() {
  if (completedThisSession.has(storageKey())) return false;
  try { return localStorage.getItem(storageKey()) !== 'done'; }
  catch { return true; }
}

export function completeOnboarding() {
  completedThisSession.add(storageKey());
  try { localStorage.setItem(storageKey(), 'done'); }
  catch { /* Storage may be unavailable in a WebView; keep this session usable. */ }
}

const steps = [
  { icon: Camera, title: 'Начните со своей коллекции', text: 'Добавьте табаки вручную или сфотографируйте пачку. После распознавания проверьте бренд и вкус — и сохраните.', hint: 'Первая цель — добавить два вкуса.' },
  { icon: Sparkles, title: 'Найдите своё сочетание', text: 'Откройте «Микс» и подберите сочетание из своей коллекции. Получите рецепт с пропорциями, а понравившийся добавьте в избранное.', hint: 'Готовые рецепты остаются в истории.' },
  { icon: Share2, title: 'Поделитесь с друзьями', text: 'Отправьте ссылку на микс или список табаков. Друг сможет открыть её в браузере без входа.', hint: 'Ссылка действует 7 дней. Её можно отключить в любой момент.' },
];

export function Onboarding({ onClose, onStart }: { onClose: () => void; onStart: () => void }) {
  const [step, setStep] = useState(0);
  const current = steps[step];
  const Icon = current.icon;
  return <Modal isOpen onClose={onClose} title="Добро пожаловать в Hookah">
    <div className="space-y-5">
      <div className="flex items-center gap-2" aria-label={`Шаг ${step + 1} из ${steps.length}`}>
        {steps.map((_, index) => <span key={index} aria-hidden="true" className="h-1 flex-1 rounded-full" style={{ background: index <= step ? 'var(--app-accent-text-color)' : 'var(--app-border)' }} />)}
        <span className="text-xs text-tg-hint ml-2">{step + 1} / {steps.length}</span>
      </div>
      <div aria-live="polite" aria-atomic="true" className="space-y-4">
        <div className="icon-tile" aria-hidden="true"><Icon className="w-6 h-6" /></div>
        <h3 className="text-2xl font-semibold leading-tight">{current.title}</h3>
        <p className="text-sm leading-relaxed text-tg-hint">{current.text}</p>
        <p className="rounded-xl bg-tg-secondary-bg p-4 text-sm leading-relaxed">{current.hint}</p>
      </div>
      <Button fullWidth onClick={() => step === steps.length - 1 ? onStart() : setStep(step + 1)}>{step === steps.length - 1 ? 'Добавить первые табаки' : 'Далее'}</Button>
      <div className="flex justify-between items-center">
        <Button variant="ghost" size="sm" disabled={step === 0} onClick={() => setStep(step - 1)}>Назад</Button>
        <Button variant="ghost" size="sm" onClick={onClose}>Пропустить</Button>
      </div>
      <p className="text-xs text-tg-hint text-center">Подсказки всегда доступны на главной: «Как пользоваться».</p>
    </div>
  </Modal>;
}

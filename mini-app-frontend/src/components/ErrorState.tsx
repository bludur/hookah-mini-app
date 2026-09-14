export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="p-6 text-tg-text" role="alert">
    <p className="mb-4">{message}</p>
    <button className="px-4 py-3 rounded-xl bg-tg-button text-tg-button-text" onClick={onRetry}>
      Повторить загрузку
    </button>
  </div>;
}

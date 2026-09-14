import { ReactNode, useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!isOpen) return;
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    element?.showModal();
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <dialog
      ref={dialog}
      aria-labelledby={title ? titleId : undefined}
      aria-label={title ? undefined : 'Диалог'}
      onCancel={event => { event.preventDefault(); onClose(); }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
      className="app-dialog m-auto p-0 w-[calc(100%-2rem)] max-w-md rounded-2xl bg-tg-section-bg text-tg-text shadow-xl backdrop:bg-black/50 open:flex open:flex-col"
      style={{ maxHeight: 'calc(var(--tg-viewport-stable-height, 100dvh) - 2rem)' }}
    >
        {/* Header */}
        {title && (
          <div className="flex shrink-0 items-center justify-between px-5 py-4 border-b border-tg-secondary-bg">
            <h2 id={titleId} className="text-lg font-semibold text-tg-text">{title}</h2>
            <button
              onClick={onClose}
              aria-label="Закрыть"
              className="w-10 h-10 flex items-center justify-center -mr-2 rounded-full hover:bg-tg-secondary-bg transition-colors tap-highlight"
            >
              <X className="w-4 h-4 text-tg-hint" />
            </button>
          </div>
        )}
        
        {/* Body */}
        <div className="min-h-0 overflow-y-auto overscroll-contain px-5 py-5">
          {children}
        </div>
    </dialog>
  );
}

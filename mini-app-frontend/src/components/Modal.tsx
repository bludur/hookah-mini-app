import { ReactNode, useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 animate-fade-in"
        onClick={onClose}
      />
      
      {/* Modal content */}
      <div className="relative w-full sm:max-w-md bg-tg-bg rounded-t-3xl sm:rounded-3xl animate-slide-up max-h-[70vh] flex flex-col">
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-tg-secondary-bg shrink-0">
            <h2 className="text-lg font-semibold text-tg-text">{title}</h2>
            <button
              onClick={onClose}
              className="p-2 -mr-2 rounded-full hover:bg-tg-secondary-bg transition-colors tap-highlight"
            >
              <X className="w-5 h-5 text-tg-hint" />
            </button>
          </div>
        )}
        
        {/* Body */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {children}
        </div>
      </div>
    </div>
  );
}

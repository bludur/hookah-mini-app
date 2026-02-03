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
      <div className="relative w-full sm:max-w-md bg-tg-bg rounded-t-2xl sm:rounded-2xl animate-slide-up">
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-3 py-2 border-b border-tg-secondary-bg">
            <h2 className="text-sm font-semibold text-tg-text">{title}</h2>
            <button
              onClick={onClose}
              className="p-1 -mr-1 rounded-full hover:bg-tg-secondary-bg transition-colors tap-highlight"
            >
              <X className="w-4 h-4 text-tg-hint" />
            </button>
          </div>
        )}
        
        {/* Body */}
        <div className="px-3 py-2">
          {children}
        </div>
      </div>
    </div>
  );
}

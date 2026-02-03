import { Loader2 } from 'lucide-react';

interface LoaderProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export function Loader({ size = 'md', text }: LoaderProps) {
  const sizeStyles = {
    sm: 'w-5 h-5',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex flex-col items-center justify-center py-8">
      <Loader2 className={`${sizeStyles[size]} animate-spin text-tg-button`} />
      {text && <p className="mt-3 text-sm text-tg-hint">{text}</p>}
    </div>
  );
}

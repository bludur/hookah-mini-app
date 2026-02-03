import { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { hapticFeedback } from '../telegram';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  loading = false,
  icon,
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-xl transition-all tap-highlight';
  
  const variantStyles = {
    primary: 'bg-tg-button text-tg-button-text hover:opacity-90',
    secondary: 'bg-tg-secondary-bg text-tg-text hover:opacity-80',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    ghost: 'bg-transparent text-tg-link hover:bg-tg-secondary-bg',
  };
  
  const sizeStyles = {
    sm: 'px-3 py-2 text-sm gap-1.5',
    md: 'px-4 py-3 text-base gap-2',
    lg: 'px-6 py-4 text-lg gap-2',
  };

  const handleClick = () => {
    if (!disabled && !loading && onClick) {
      hapticFeedback.light();
      onClick();
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={disabled || loading}
      className={`
        ${baseStyles}
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${fullWidth ? 'w-full' : ''}
        ${disabled || loading ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {loading ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : (
        <>
          {icon}
          {children}
        </>
      )}
    </button>
  );
}

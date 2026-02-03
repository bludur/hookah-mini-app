import { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
      <div className="text-tg-hint mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-tg-text mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-tg-hint mb-6 max-w-xs">{description}</p>
      )}
      {action}
    </div>
  );
}

import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from './Button';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'Failed to load data from BRIDGE API. Please check your connection and try again.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center bg-rose-500/5 border border-rose-500/20 rounded-xl my-4 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-rose-500/15 flex items-center justify-center text-rose-400 mb-3">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-rose-200">{title}</h4>
      <p className="text-sm text-slate-400 max-w-md mt-1 mb-4">{message}</p>
      {onRetry && (
        <Button
          size="sm"
          variant="outline"
          leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          onClick={onRetry}
        >
          Try Again
        </Button>
      )}
    </div>
  );
};


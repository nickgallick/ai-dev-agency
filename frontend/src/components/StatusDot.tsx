import React from 'react';

interface StatusDotProps {
  status: 'connected' | 'degraded' | 'disconnected' | 'disabled';
  size?: 'sm' | 'md' | 'lg';
  animate?: boolean;
}

const statusColors: Record<string, string> = {
  connected: 'bg-accent-success',
  degraded: 'bg-accent-warning',
  disconnected: 'bg-accent-error',
  disabled: 'bg-text-tertiary',
};

const sizeClasses: Record<string, string> = {
  sm: 'w-2 h-2',
  md: 'w-3 h-3',
  lg: 'w-4 h-4',
};

export function StatusDot({ status, size = 'md', animate = true }: StatusDotProps) {
  const isActive = status === 'connected';
  
  return (
    <span className="relative inline-flex">
      <span
        className={`rounded-full ${statusColors[status]} ${sizeClasses[size]}`}
      />
      {animate && isActive && (
        <span
          className={`absolute inset-0 rounded-full ${statusColors[status]} animate-ping opacity-75`}
          style={{ animationDuration: '2s' }}
        />
      )}
    </span>
  );
}

export default StatusDot;

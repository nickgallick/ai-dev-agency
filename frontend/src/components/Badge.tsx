import { clsx } from 'clsx'

type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'default'

interface BadgeProps {
  variant?: BadgeVariant
  children: React.ReactNode
  className?: string
  pulse?: boolean
}

export function Badge({ variant = 'default', children, className, pulse }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        variant === 'success' && 'bg-accent-success/10 text-accent-success',
        variant === 'warning' && 'bg-accent-warning/10 text-accent-warning',
        variant === 'error' && 'bg-accent-error/10 text-accent-error',
        variant === 'info' && 'bg-accent-primary/10 text-accent-primary',
        variant === 'default' && 'bg-text-tertiary/10 text-text-tertiary',
        pulse && 'animate-pulse',
        className
      )}
    >
      {children}
    </span>
  )
}

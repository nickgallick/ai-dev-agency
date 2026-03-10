import { ReactNode } from 'react'
import { clsx } from 'clsx'

interface BadgeProps {
  children: ReactNode
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'running'
  className?: string
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  const variantClass = {
    default: 'badge-default',
    success: 'badge-success',
    warning: 'badge-warning',
    error: 'badge-error',
    info: 'badge-info',
    running: 'badge-running'
  }[variant]

  return (
    <span className={clsx('badge', variantClass, className)}>
      {children}
    </span>
  )
}

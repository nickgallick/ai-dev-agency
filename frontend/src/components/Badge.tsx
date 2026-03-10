import { ReactNode } from 'react'
import { clsx } from 'clsx'

export interface BadgeProps {
  children: ReactNode
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'running'
  className?: string
  pulse?: boolean
}

export function Badge({ children, variant = 'default', className, pulse }: BadgeProps) {
  const variantClass = {
    default: 'badge-default',
    success: 'badge-success',
    warning: 'badge-warning',
    error: 'badge-error',
    info: 'badge-info',
    running: 'badge-running'
  }[variant]

  return (
    <span className={clsx('badge', variantClass, pulse && 'animate-pulse', className)}>
      {children}
    </span>
  )
}

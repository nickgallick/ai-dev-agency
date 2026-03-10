import { ReactNode } from 'react'
import { clsx } from 'clsx'

interface CardProps {
  children: ReactNode
  className?: string
  variant?: 'default' | 'elevated' | 'iridescent'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  onClick?: () => void
}

export function Card({ 
  children, 
  className, 
  variant = 'default',
  padding = 'md',
  onClick 
}: CardProps) {
  const baseClass = {
    default: 'glass-card',
    elevated: 'glass-card-elevated',
    iridescent: 'glass-card-iridescent'
  }[variant]

  const paddingStyles = {
    none: { padding: 0 },
    sm: { padding: 'var(--space-3)' },
    md: { padding: 'var(--space-5)' },
    lg: { padding: 'var(--space-6)' }
  }[padding]

  return (
    <div 
      className={clsx(baseClass, className, onClick && 'cursor-pointer')}
      style={paddingStyles}
      onClick={onClick}
    >
      {variant === 'elevated' && <div className="bloom-warm" />}
      {variant === 'elevated' && <div className="bloom-cool" />}
      <div className={variant === 'elevated' ? 'bloom-content' : undefined}>
        {children}
      </div>
    </div>
  )
}

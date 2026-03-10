import { ReactNode, ButtonHTMLAttributes } from 'react'
import { clsx } from 'clsx'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost' | 'iridescent' | 'icon'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md',
  isLoading,
  className,
  disabled,
  ...props 
}: ButtonProps) {
  const variantClass = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    iridescent: 'btn-iridescent',
    icon: 'btn-icon btn-ghost'
  }[variant]

  const sizeStyles = {
    sm: { padding: 'var(--space-2) var(--space-3)', fontSize: 'var(--text-sm)', minHeight: '36px' },
    md: { padding: 'var(--space-3) var(--space-5)', fontSize: 'var(--text-base)', minHeight: '44px' },
    lg: { padding: 'var(--space-4) var(--space-6)', fontSize: 'var(--text-lg)', minHeight: '52px' }
  }[size]

  return (
    <button
      className={clsx('btn', variantClass, className)}
      style={sizeStyles}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading...
        </span>
      ) : children}
    </button>
  )
}

import { clsx } from 'clsx'
import { HTMLAttributes, forwardRef } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, padding = 'md', children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'bg-background-secondary border border-border-subtle rounded-lg',
          padding === 'sm' && 'p-3',
          padding === 'md' && 'p-4 lg:p-5',
          padding === 'lg' && 'p-6 lg:p-8',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

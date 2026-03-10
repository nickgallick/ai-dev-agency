import { clsx } from 'clsx'
import { InputHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="block text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={clsx(
            'w-full px-4 py-2.5 bg-background-input border rounded-[10px] text-text-primary',
            'placeholder:text-text-tertiary',
            'focus:outline-none focus:ring-2 focus:ring-border-focus focus:border-border-focus',
            'transition-colors',
            error ? 'border-accent-error' : 'border-border-subtle',
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-sm text-accent-error">{error}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

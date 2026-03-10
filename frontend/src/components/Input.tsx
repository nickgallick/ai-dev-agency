import { InputHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'hero'
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ variant = 'default', label, error, className, ...props }, ref) => {
    const inputClass = variant === 'hero' ? 'glass-input-hero' : 'glass-input'
    
    return (
      <div className="w-full">
        {label && (
          <label 
            className="block mb-2 text-sm font-medium" 
            style={{ color: 'var(--text-secondary)' }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={clsx(inputClass, error && 'border-red-500', className)}
          {...props}
        />
        {error && (
          <p className="mt-1 text-sm" style={{ color: 'var(--accent-error)' }}>
            {error}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

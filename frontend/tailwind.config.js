/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── Backgrounds ──────────────────────────────────────────────────
        // bg-background-* (legacy names) + bg-bg-* (short names)
        background: {
          primary:   'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary:  'var(--bg-tertiary)',
          input:     'var(--bg-tertiary)',
        },
        // Short aliases: bg-bg-primary, bg-bg-secondary, etc.
        bg: {
          base:      'var(--bg-base)',
          primary:   'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary:  'var(--bg-tertiary)',
          elevated:  'var(--bg-elevated)',
        },

        // ── Borders ───────────────────────────────────────────────────────
        border: {
          subtle:  'var(--border-subtle)',
          default: 'var(--border-default)',
          focus:   'var(--border-focus)',
        },

        // ── Text ─────────────────────────────────────────────────────────
        text: {
          primary:   'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary:  'var(--text-tertiary)',
          muted:     'var(--text-muted)',
        },

        // ── Accents (with opacity-modifier support via RGB channels) ──────
        accent: {
          primary:       'rgb(var(--accent-primary-rgb) / <alpha-value>)',
          'primary-hover': 'rgb(var(--accent-primary-rgb) / <alpha-value>)',
          secondary:     'rgb(var(--accent-secondary-rgb) / <alpha-value>)',
          success:       'rgb(var(--accent-success-rgb) / <alpha-value>)',
          warning:       'rgb(var(--accent-warning-rgb) / <alpha-value>)',
          error:         'rgb(var(--accent-error-rgb) / <alpha-value>)',
          purple:        'rgb(var(--accent-purple-rgb) / <alpha-value>)',
        },
      },

      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },

      fontSize: {
        'xs':  '0.75rem',
        'sm':  '0.8125rem',
        'base':'0.875rem',
        'lg':  '1rem',
        'xl':  '1.25rem',
        '2xl': '1.5rem',
        '3xl': '1.875rem',
        '4xl': '2.25rem',
        '5xl': '3rem',
      },

      borderRadius: {
        'DEFAULT': '8px',
        'lg': '12px',
        'xl': '16px',
        '2xl': '24px',
      },

      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}

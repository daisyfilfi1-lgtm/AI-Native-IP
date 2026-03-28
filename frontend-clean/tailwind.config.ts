import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // AI-Native IP Factory Design System
        background: {
          DEFAULT: '#0a0a0f',
          secondary: '#12121a',
          tertiary: '#1a1a25',
          elevated: '#222230',
        },
        foreground: {
          DEFAULT: '#fafafa',
          secondary: '#a1a1aa',
          tertiary: '#71717a',
          muted: '#52525b',
        },
        primary: {
          DEFAULT: '#8b5cf6',
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        accent: {
          DEFAULT: '#06b6d4',
          purple: '#a855f7',
          blue: '#3b82f6',
          cyan: '#06b6d4',
          pink: '#ec4899',
          green: '#10b981',
          yellow: '#f59e0b',
          red: '#ef4444',
        },
        border: {
          DEFAULT: '#27272a',
          hover: '#3f3f46',
          active: '#52525b',
        },
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      animation: {
        'gradient': 'gradient 8s linear infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'gradient-ai': 'linear-gradient(135deg, #8b5cf6 0%, #06b6d4 50%, #ec4899 100%)',
      },
      boxShadow: {
        'glow': '0 0 40px -10px rgba(139, 92, 246, 0.3)',
        'glow-lg': '0 0 60px -15px rgba(139, 92, 246, 0.4)',
        'glow-cyan': '0 0 40px -10px rgba(6, 182, 212, 0.3)',
      },
    },
  },
  plugins: [],
}

export default config

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Telegram theme colors
        'tg-bg': 'var(--app-bg-color, #ffffff)',
        'tg-text': 'var(--app-text-color, #000000)',
        'tg-hint': 'var(--app-hint-color, #999999)',
        'tg-link': 'var(--app-link-color, #2481cc)',
        'tg-button': 'var(--app-button-color, #2481cc)',
        'tg-button-text': 'var(--app-button-text-color, #ffffff)',
        'tg-secondary-bg': 'var(--app-secondary-bg-color, #f1f1f1)',
        'tg-header-bg': 'var(--app-header-bg-color, #ffffff)',
        'tg-accent': 'var(--app-accent-text-color, #2481cc)',
        'tg-section-bg': 'var(--app-section-bg-color, #ffffff)',
        'tg-section-header': 'var(--app-section-header-text-color, #999999)',
        'tg-subtitle': 'var(--app-subtitle-text-color, #999999)',
        'tg-destructive': 'var(--app-destructive-text-color, #ff3b30)',
      },
      animation: {
        'slide-up': 'slideUp 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}

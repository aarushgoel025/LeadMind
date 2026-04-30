/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0F1117',
        surface: '#1A1D27',
        'surface-elevated': '#222536',
        border: '#2E3148',
        critical: '#EF4444',
        warning: '#F59E0B',
        suggestion: '#3B82F6',
        success: '#10B981',
        'text-primary': '#F1F5F9',
        'text-secondary': '#94A3B8',
        'armorclaw-accent': '#8B5CF6',
        'armoriq-accent': '#06B6D4'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}

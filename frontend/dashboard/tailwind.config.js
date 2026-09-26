/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F2F0EA',
        'paper-2': '#E9E6DE',
        panel: '#FFFFFF',
        ink: '#101010',
        dim: '#57544D',
        faint: '#8B877D',
        rule: '#101010',
        'rule-soft': '#C8C4BA',
        red: { DEFAULT: '#D9202C', soft: '#FBE9EA' },
        orange: { DEFAULT: '#E8590C', soft: '#FCEDE4' },
        green: { DEFAULT: '#1E7A38', soft: '#E7F2E9' },
      },
      fontFamily: {
        grotesk: ['Archivo', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: { none: '0', sm: '2px', md: '4px', lg: '6px' },
      boxShadow: {
        hard: '4px 4px 0 0 #101010',
        'hard-sm': '2px 2px 0 0 #101010',
        none: 'none',
      },
    },
  },
  plugins: [],
}

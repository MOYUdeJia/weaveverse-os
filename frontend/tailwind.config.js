/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          'Segoe UI',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      colors: {
        ink: '#16201d',
        moss: '#3f6f57',
        ember: '#d77245',
        dawn: '#f4efe7',
        aurora: '#5c79a8',
      },
      boxShadow: {
        glow: '0 22px 80px rgba(63, 111, 87, 0.24)',
      },
    },
  },
  plugins: [],
}

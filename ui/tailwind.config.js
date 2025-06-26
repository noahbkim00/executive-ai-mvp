import forms from '@tailwindcss/forms';

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0F2622',
        surface: '#1A3A32',
        primary: '#F97316',
        secondary: '#10B981',
        accent: '#FFB800',
        'text-primary': '#FFFFFF',
        'text-secondary': '#9CA3AF',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [forms],
}
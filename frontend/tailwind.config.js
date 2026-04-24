// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: false, // disable dark mode
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Add any custom colors or spacing if needed
    },
  },
  plugins: [],
};

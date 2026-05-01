import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        glow: '0 0 60px rgba(129, 140, 248, 0.25)',
      },
    },
  },
  plugins: [],
};

export default config;
